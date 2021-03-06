from SharedCode.copper import OWASPCopper
import logging

import azure.functions as func

import os
import json
import hashlib
import base64
import html
import markdown
from datetime import datetime
from datetime import timedelta
from typing import Dict

from ..SharedCode import github
from ..SharedCode.eventbot import registrant
from ..SharedCode import copper
from ..SharedCode.googleapi import OWASPGoogle

import stripe

from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError
mailchimp = MailChimp(mc_api=os.environ["MAILCHIMP_API_KEY"])

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
        handle_checkout_session_completed(event_data)
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

    
    return func.HttpResponse(status_code=200)

def handle_checkout_session_completed(event: Dict):
    payment_intent = event.get('payment_intent', None)
    subscription = event.get('subscription', None)
    customer_id = event.get('customer', None)
    customer_email = event.get('customer_email', None)
    setup_intent = event.get('setup_intent', None)
    subscription_data = {}
    metadata = {}
    if payment_intent is not None:
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent,
            api_key=os.environ["STRIPE_SECRET"]
        )

    if customer_email is None:
        customer_email = get_customer_email_from_id(customer_id)

    if setup_intent is not None:
        setup_intent = stripe.SetupIntent.retrieve(
            setup_intent,
            api_key=os.environ["STRIPE_SECRET"]
        )
        metadata = setup_intent.get('metadata', {})
        customer_id = metadata.get('customer_id', None)
        subscription_id = metadata.get('subscription_id', None)
        payment_method = setup_intent.get('payment_method', None)
        stripe.PaymentMethod.attach(
            payment_method,
            customer=customer_id,
            api_key=os.environ["STRIPE_SECRET"]
        )
        stripe.Subscription.modify(
            subscription_id,
            default_payment_method=payment_method,
            api_key=os.environ["STRIPE_SECRET"]
        )
    elif payment_intent is not None and payment_intent['metadata'].get('purchase_type') == 'event':
        metadata = payment_intent.get('metadata', {})
        create_order_from_payment_intent(payment_intent)
        add_event_registrant_to_mailing_list(customer_email, metadata)
    else:
        payment_id = None
        if payment_intent is not None:
            payment_id = payment_intent.get('id', None)
            metadata = payment_intent.get('metadata', {})
            purchase_type = metadata.get('purchase_type', 'donation')
            
            if purchase_type == 'membership':
                subscription_data = get_subscription_data_from_event(event)

        if subscription is not None:
            subscription = stripe.Subscription.retrieve(
                subscription,
                api_key=os.environ["STRIPE_SECRET"]
            )
            metadata = subscription.get('metadata', {})
            purchase_type = metadata.get('purchase_type', 'donation')

            if purchase_type == 'membership':
                subscription_data = get_subscription_data(subscription)
        price = event.get('price', None) # this was working
        if price == None:
            price = event.get('amount', None)
        if price == None:
            price = event.get('amount_total', 0)
        update_customer_record(customer_id, metadata, subscription_data, payment_id, price)
        add_to_mailing_list(customer_email, metadata, subscription_data, customer_id)
        
        attribution = metadata.get('attribution', 'False')
        if attribution == 'True':
            attribute_donation(metadata)


def update_customer_record(customer_id, metadata, subscription_data, payment_id, monetary_value):
    if metadata.get('purchase_type') == 'membership':

        if (metadata.get('recurring', 'False') == 'True'):
            recurring = 'yes'
        else:
            recurring = 'no'

        customer = stripe.Customer.retrieve(
            customer_id,
            expand=['subscriptions'],
            api_key=os.environ["STRIPE_SECRET"]
        )

        existing_subscriptions = customer.get('subscriptions')
        for subscription in existing_subscriptions:
            if subscription['plan']['nickname'] is not None and "Membership" in subscription['plan']['nickname'] and subscription['id'] != subscription_data['subscription_id']:
                stripe.Subscription.delete(
                    subscription['id'],
                    api_key=os.environ["STRIPE_SECRET"]
                )


        customer_metadata = customer.get('metadata', {})
        customer_name = metadata.get('name')
        if customer_name == None:
            customer_name = customer.get('name')
        if customer_name == None:
            customer_name = customer.get('email')

        membership_end = customer_metadata.get('membership_end', None)
        membership_start = customer_metadata.get('membership_start', None)
        if membership_start == None or membership_start == '':
            membership_start = subscription_data['membership_start']
        else:
            try:
                membership_start = datetime.strptime(membership_start, "%m/%d/%Y")
            except:
                try:
                    membership_start = datetime.strptime(membership_start, "%Y-%m-%d")
                except:
                    pass

        # if already a membership, we must add the days to the end
        if membership_end is not None and subscription_data['membership_type'] != 'lifetime':
            end_object = datetime.strptime(membership_end, '%m/%d/%Y')
            if end_object > datetime.now() and subscription_data['days_added'] != None:
                new_end_date = end_object + timedelta(days=subscription_data['days_added'])
                subscription_data['membership_end'] = new_end_date.strftime('%m/%d/%Y')

                if new_end_date < datetime.now() + timedelta(days=730):
                    if subscription_data['subscription_id'] is not None:
                        stripe.Subscription.modify(
                            subscription_data['subscription_id'],
                            trial_end=int(new_end_date.timestamp()),
                            prorate=False,
                            api_key=os.environ["STRIPE_SECRET"]
                        )
                else:
                    if subscription_data['subscription_id'] is not None:
                        stripe.Subscription.delete(
                            subscription_data['subscription_id'],
                            api_key=os.environ["STRIPE_SECRET"]
                        )
                        recurring="no"
        subscription_data['membership_recurring'] = recurring
        subscription_data['membership_start'] = membership_start.strftime('%m/%d/%Y')
        
        stripe.Customer.modify(
            customer_id,
            metadata={
                "membership_start": subscription_data['membership_start'],
                "membership_type": subscription_data['membership_type'],
                "membership_end": subscription_data['membership_end'],
                "membership_recurring": subscription_data['membership_recurring']
            },
            api_key=os.environ["STRIPE_SECRET"]
        )
        
        customer_email = customer.get('email')
        
        try:
            if monetary_value > 500: # most likely in 5000 = 50.00 format as there is no membership for individuals > 500.00
                monetary_value = monetary_value * .01
            cop = OWASPCopper()
            cop.CreateOWASPMembership(customer_id, payment_id, customer_name, customer_email, subscription_data, monetary_value)
            
        except Exception as err:
            logging.error(f'Failed to create Copper data: {err}')
    
def get_subscription_data_from_event(event):
    description = event["display_items"][0]["custom"]["description"]
    
    if "One Year" in description:
        membership_type = 'one'
        period_end = datetime.now() + timedelta(days=365)
        period_end = period_end.strftime('%m/%d/%Y')
        add_days = 365
    elif "Two Year" in description:
        membership_type = 'two'
        period_end = datetime.now() + timedelta(days=730)
        period_end = period_end.strftime('%m/%d/%Y')
        add_days = 730
    elif "Lifetime" in description:
        membership_type = 'lifetime'
        period_end = None
        add_days = None
    # no need to worry with complimentary here as it isn't an option to pay for in Stripe

    return {
        "membership_start": datetime.now(),
        "membership_end": period_end,
        "membership_type": membership_type,
        "days_added": add_days,
        "subscription_id": None
    }


def get_subscription_data(subscription):
    period_end = datetime.utcfromtimestamp(subscription["current_period_end"]).strftime('%m/%d/%Y')
    membership_type = 'one'
    add_days = 365

    return {
        "membership_start": datetime.now(),
        "membership_end": period_end,
        "membership_type": membership_type,
        "days_added": add_days,
        "subscription_id": subscription.id
    }


def add_to_mailing_list(email, metadata, subscription_data, customer_id):
    subscriber_hash = get_mailchimp_subscriber_hash(email)

    request_data = {
        "email_address": email,
        "status_if_new": "subscribed",
        "status": "subscribed",
        "merge_fields": get_merge_fields(metadata, subscription_data, customer_id),
        "interests": get_interests(metadata),
        "marketing_permissions": get_marketing_permissions(metadata)
    }

    list_member = mailchimp.lists.members.create_or_update(os.environ["MAILCHIMP_LIST_ID"], subscriber_hash, request_data)

    return list_member


def add_event_registrant_to_mailing_list(email, metadata):
    subscriber_hash = get_mailchimp_subscriber_hash(email)

    first_name = metadata.get('name').strip().split(' ')[0]
    last_name = ' '.join((metadata.get('name') + ' ').split(' ')[1:]).strip()

    merge_fields = {}
    merge_fields['NAME'] = metadata.get('name')
    merge_fields['FNAME'] = first_name
    merge_fields['LNAME'] = last_name

    if metadata.get('company', None) is not None:
        merge_fields['COMPANY'] = metadata.get('company')
    if metadata.get('country', None) is not None:
        merge_fields['COUNTRY'] = metadata.get('country')

    request_data = {
        "email_address": email,
        "status_if_new": "subscribed",
        "status": "subscribed",
        "merge_fields": merge_fields,
        "marketing_permissions": get_marketing_permissions(metadata)
    }

    list_member = mailchimp.lists.members.create_or_update(
        os.environ["MAILCHIMP_LIST_ID"],
        subscriber_hash,
        request_data
    )

    product = stripe.Product.retrieve(
        metadata.get('event_id'),
        api_key=os.environ["STRIPE_SECRET"]
    )

    event_date = product['metadata'].get('event_date', None)
    if event_date is None:
        event_year = datetime.now().year
    else:
        event_year = datetime.strptime(event_date, '%Y-%m-%d').year
    segment_name = str(event_year) + ' ' + str(product['name'])

    segments = mailchimp.lists.segments.all(os.environ['MAILCHIMP_LIST_ID'], True)
    segment_id = None
    for segment in segments['segments']:
        if segment['name'] == segment_name:
            segment_id = segment['id']
            break

    if segment_id is None:
        segment = mailchimp.lists.segments.create(os.environ['MAILCHIMP_LIST_ID'], {
            'name': segment_name,
            'static_segment': []
        })
        segment_id = segment['id']

    mailchimp.lists.segments.members.create(
        os.environ['MAILCHIMP_LIST_ID'],
        segment_id,
        {
            'email_address': email,
            'status': 'subscribed'
        }
    )

    return list_member


def get_marketing_permissions(metadata):
    if metadata.get('mailing_list', 'False') == 'True':
        return [
            {
                "marketing_permission_id": os.environ["MAILCHIMP_MKTG_PERMISSIONS_ID"],
                "enabled": True
            }
        ]
    else:
        return [
            {
                "marketing_permission_id": os.environ["MAILCHIMP_MKTG_PERMISSIONS_ID"],
                "enabled": False
            }
        ]


def get_interests(metadata):
    purchase_type = metadata.get('purchase_type')

    if purchase_type == 'donation':
        return {
            os.environ["MAILCHIMP_DONOR_GROUP_ID"]: True
        }
    else:
        return {
            os.environ["MAILCHIMP_MEMBER_GROUP_ID"]: True
        }


def get_merge_fields(metadata, subscription_data, customer_id):
    merge_fields = {}

    purchase_type = metadata.get('purchase_type', 'donation')
    name = metadata.get('name')
    source = metadata.get('source')

    merge_fields['NAME'] = name

    if source is not None:
        merge_fields['SOURCE'] = source

    if purchase_type == 'membership':
        company = metadata.get('company')
        country = metadata.get('country')
        postal_code = metadata.get('postal_code')

        merge_fields['MEMSTART'] = datetime.today().strftime('%m/%d/%Y')

        customer = stripe.Customer.retrieve(
            customer_id,
            api_key=os.environ["STRIPE_SECRET"]
        )
        customer_metadata = customer.get('metadata', {})

        membership_end = customer_metadata.get('membership_end', '') #should this return 'NULL' string and then compare via None as below?  Changed to ''
        membership_type = customer_metadata.get('membership_type', '')
        membership_recurring = customer_metadata.get('membership_recurring', 'no')

        if membership_end is not None:
            merge_fields['MEMEND'] = membership_end
        if membership_type is not None:
            merge_fields['MEMTYPE'] = membership_type
        if membership_recurring is not None:
            merge_fields['MEMRECUR'] = membership_recurring
        if company is not None:
            merge_fields['COMPANY'] = company
        if country is not None:
            merge_fields['COUNTRY'] = country
        if postal_code is not None:
            merge_fields['POSTALCODE'] = postal_code

    return merge_fields


def attribute_donation(metadata):
    repo_name = metadata.get('repo_name', None)
    donor_name = metadata.get('name', None)
    donor_file = '_data/ow_attributions.json'
    donor_name = html.escape(donor_name)

    if repo_name is not None and donor_name is not None and repo_name.startswith('www'):
        gh = github.OWASPGitHub()
        existing_file = gh.GetFile(repo_name, donor_file)

        sha = ''

        if not gh.TestResultCode(existing_file.status_code):
            donors = [donor_name]
        else:
            donors = json.loads(existing_file.text)
            sha = donors['sha']
            file_text = base64.b64decode(donors['content']).decode('utf-8')
            donors = json.loads(file_text)
            donors.append(donor_name)

        file_contents = json.dumps(donors)
        gh.UpdateFile(repo_name, donor_file, file_contents, sha)


def get_mailchimp_subscriber_hash(email):
    email = email.lower()
    hashed = hashlib.md5(email.encode('utf8'))

    return hashed.hexdigest()


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


def create_order_from_payment_intent(payment_intent):
    skus = payment_intent.get('metadata', {}).get('skus', '').split('|')
    order_total = 0
    order_items = []

    for sku in skus:
        stripe_sku = stripe.SKU.retrieve(
            sku,
            api_key=os.environ["STRIPE_SECRET"]
        )
        order_total += stripe_sku.get('price', 0)
        order_items.append({
            "amount": stripe_sku.get('price', 0),
            "currency": payment_intent.get('currency', 'usd'),
            "description": stripe_sku['attributes']['name'],
            "parent": sku,
            "quantity": 1,
            "type": "sku"
        })

    if order_total > payment_intent.get('amount', 0):
        order_items.append({
            "amount": payment_intent['amount'] - order_total,
            "currency": payment_intent.get('currency', 'usd'),
            "description": 'Discount',
            "quantity": 1,
            "type": "discount"
        })

    metadata = payment_intent.get('metadata', {})
    metadata['charge_id'] = payment_intent['charges']['data'][0]['id']

    order = stripe.Order.create(
        currency=payment_intent.get('currency', 'usd'),
        customer=payment_intent['customer'],
        metadata=metadata,
        items=order_items,
        api_key=os.environ["STRIPE_SECRET"]
    )

    if metadata.get('discount_code', None) is not None:
        increment_discount_code(metadata.get('discount_code'))


def increment_discount_code(discount_code):
    try:
        discount_code = discount_code.strip().upper()
        coupon = stripe.Coupon.retrieve(
            discount_code,
            api_key=os.environ["STRIPE_SECRET"]
        )
        metadata = coupon.get('metadata', {})
        uses = int(metadata.get('uses', 0)) + 1
        stripe.Coupon.modify(
            discount_code,
            metadata={"uses": uses},
            api_key=os.environ["STRIPE_SECRET"]
        )
    except Exception as exception:
        pass


def get_customer_email_from_id(customer_id):
    customer = stripe.Customer.retrieve(
        customer_id,
        api_key=os.environ["STRIPE_SECRET"]
    )
    return customer.email
