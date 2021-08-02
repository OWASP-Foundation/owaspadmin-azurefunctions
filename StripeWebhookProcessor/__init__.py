import logging

import azure.functions as func

import os
import json
import base64
import html
import markdown

from ..SharedCode import github
from ..SharedCode.eventbot import registrant

import stripe


def main(req: func.HttpRequest, chmsg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    payload = req.get_json()
    event = None

    try:
        event = stripe.Event.construct_from(
            payload, os.environ["STRIPE_SECRET"]
        )
    except ValueError as e:
        return func.HttpResponse(status_code=400)

    event_data = event.data.object

    if event.type == 'checkout.session.completed':
        chmsg.set(json.dumps({ 'job_type': event.type, 'payload': event_data }))
    elif event.type == 'product.created':
        handle_product_created(event_data)
    elif event.type == 'sku.created':
        handle_sku_created(event_data)
    elif event.type == 'sku.updated':
        handle_sku_updated(event_data)
    elif event.type == 'order.created':
        chmsg.set(json.dumps({ 'job_type': event.type, 'payload': event_data }))
    elif event.type == 'charge.refunded':
        chmsg.set(json.dumps({ 'job_type': event.type, 'payload': event_data }))
    elif event.type == 'invoice.paid' and (event_data['billing_reason'] == 'subscription_create' or event_data['billing_reason'] == 'subscription_cycle') : # this could be any invoice but also includes things like subscriptions....
        chmsg.set(json.dumps({ 'job_type': event.type, 'payload': event_data }))
        
    return func.HttpResponse(status_code=200)


def handle_product_created(event_data):
    metadata = event_data.get('metadata', {})

    if metadata.get('type', None) == 'event':
        product_file = '_data/products.json'
        repo_name = metadata.get('repo_name', None)
        event_name = event_data.get('name', None)

        gh = github.OWASPGitHub()
        existing_file = gh.GetFile(repo_name, product_file)

        sha = ''

        if gh.TestResultCode(existing_file.status_code):
            products = json.loads(existing_file.text)
            sha = products['sha']

        product_listing = {
            'id': event_data.get('id', None),
            'name': event_name,
            'currency': metadata.get('currency', 'usd'),
            'products': []
        }

        file_contents = json.dumps(product_listing)
        gh.UpdateFile(repo_name, product_file, file_contents, sha)

        registrant.create_spreadsheet(event_data)


def handle_sku_updated(event_data):
    product = stripe.Product.retrieve(
        event_data.get('product', None),
        api_key=os.environ["STRIPE_SECRET"]
    )
    product_metadata = product.get('metadata', {})

    if product_metadata.get('type', None) == 'event':
        product_file = '_data/products.json'
        repo_name = product_metadata.get('repo_name', None)

        gh = github.OWASPGitHub()
        existing_file = gh.GetFile(repo_name, product_file)

        if gh.TestResultCode(existing_file.status_code):
            products = json.loads(existing_file.text)
            sha = products['sha']

            event_data['metadata']['description'] = markdown.markdown(event_data['metadata'].get('description', ''), extensions=['markdown.extensions.nl2br'])

            file_text = base64.b64decode(products['content']).decode('utf-8')
            products = json.loads(file_text)

            if event_data['active'] is False:
                for i in range(len(products['products'])):
                    if products['products'][i]['id'] == event_data['id']:
                        del products['products'][i]
                        break
            else:
                for product in products['products']:
                    if product['id'] == event_data['id']:
                        product['name'] = event_data['attributes']['name']
                        product['amount'] = event_data['price']
                        product['metadata'] = event_data['metadata']
                        break

            file_contents = json.dumps(
                products,
                ensure_ascii=False,
                indent=4
            )
            gh.UpdateFile(repo_name, product_file, file_contents, sha)


def handle_sku_created(event_data):
    product = stripe.Product.retrieve(
        event_data.get('product', None),
        api_key=os.environ["STRIPE_SECRET"]
    )
    product_metadata = product.get('metadata', {})
    sku_attributes = event_data.get('attributes', {})
    sku_metadata = event_data.get('metadata', {})

    if product_metadata.get('type', None) == 'event':
        product_file = '_data/products.json'
        repo_name = product_metadata.get('repo_name', None)

        gh = github.OWASPGitHub()
        existing_file = gh.GetFile(repo_name, product_file)

        if gh.TestResultCode(existing_file.status_code):
            products = json.loads(existing_file.text)
            sha = products['sha']

            sku_metadata['description'] = markdown.markdown(sku_metadata.get('description', ''), extensions=['markdown.extensions.nl2br'])

            file_text = base64.b64decode(products['content']).decode('utf-8')
            products = json.loads(file_text)
            products['products'].append({
                'id': event_data.get('id', None),
                'name': sku_attributes.get('name', None),
                'amount': event_data.get('price', None),
                'metadata': sku_metadata
            })

            file_contents = json.dumps(
                products,
                ensure_ascii=False,
                indent=4
            )
            gh.UpdateFile(repo_name, product_file, file_contents, sha)
