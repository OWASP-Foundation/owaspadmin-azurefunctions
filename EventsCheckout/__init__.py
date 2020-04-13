import logging

import azure.functions as func

import os
import json
import pathlib
import datetime
from typing import Dict

import stripe

import urllib.parse

def main(req: func.HttpRequest) -> func.HttpResponse:
    request = req.get_json()
    errors = validate_request(request)

    try:
        line_items = get_line_items(request)
    except Exception as error:
        errors['sku'] = ['Invalid ticket option selected']

    if not bool(errors):
        is_comp_order = is_order_comped(line_items)
        if is_comp_order is True:
            response = create_comp_order(request, line_items)
            return return_response(response, True)
        else:
            line_items = normalize_line_items(line_items)
            response = create_checkout_session(request, line_items)
            return return_response(response, True)
    else:
        return return_response(errors, False)


def validate_request(request: Dict) -> Dict:
    errors = {}

    if request.get('sku', None) is None:
        errors['sku'] = ['Please select the ticket option that you would like to purchase']
    if request.get('name', None) is None:
        errors['name'] = ['Name is required']
    if request.get('email', None) is None:
        errors['email'] = ['Email is required']

    if request.get('discount_code', None) is not None and request.get('discount_code', None) is not '':
        try:
            coupon = stripe.Coupon.retrieve(
                request.get('discount_code').strip().upper(),
                api_key=os.environ["STRIPE_SECRET"]
            )
            metadata = coupon.get('metadata', {})
            product = stripe.Product.retrieve(
                metadata.get('event_id'),
                api_key=os.environ["STRIPE_SECRET"]
            )
            sku = stripe.SKU.retrieve(
                request.get('sku')[0],
                api_key=os.environ["STRIPE_SECRET"]
            )
            sku_metadata = sku.get('metadata', {})
            if sku.get('product') != product['id'] or metadata.get('event_id') != product['id']:
                errors['discount_code'] = ['This discount is not valid']
        except Exception as err:
            errors['discount_code'] = ['This discount is not valid']

    return errors


def get_line_items(request):
    event_id = None
    skus = request.get('sku', [])
    line_items = []
    total_discount = 0
    available_discount = 0
    comp_discount = False

    if request.get('discount_code', None) is not None:
        try:
            coupon = stripe.Coupon.retrieve(
                request.get('discount_code').strip().upper(),
                api_key=os.environ["STRIPE_SECRET"]
            )
            metadata = coupon.get('metadata', {})
            available_discount = coupon.get('amount_off', 0)
            if coupon.get('percent_off', 0) == 100:
                comp_discount = True
                available_discount = 0
        except Exception as exception:
            pass

    for sku in skus:
        stripe_sku = stripe.SKU.retrieve(
            sku,
            api_key=os.environ["STRIPE_SECRET"]
        )
        sku_metadata = stripe_sku.get('metadata', {})
        
        # check that all skus belong to the same product
        if event_id is None:
            event_id = stripe_sku['product']
        else:
            if event_id != stripe_sku['product']:
                raise Exception('All products must belong to the same event')

        # check that sku is active
        if stripe_sku['active'] is False:
            raise Exception('Invalid product')

        # check that sku is available now
        if sku_metadata.get('display_start', None) is not None or sku_metadata.get('display_end', None) is not None:
            if sku_metadata.get('display_start', None) is not None:
                start_datetime = datetime.datetime.strptime(sku_metadata['display_start'], "%Y-%m-%d")
                if start_datetime > datetime.datetime.now():
                    raise Exception('Invalid product')
            if sku_metadata.get('display_end', None) is not None:
                end_datetime = datetime.datetime.strptime(sku_metadata['display_end'], "%Y-%m-%d")
                if end_datetime < datetime.datetime.now():
                    raise Exception('Invalid product')

        # check that sku has available inventory
        if sku_metadata.get('inventory', None) is not None and sku_metadata.get('purchased', None) is not None:
            if sku_metadata['inventory'] <= sku_metadata['purchased']:
                raise Exception('Product sold out')

        product_name = stripe_sku['attributes']['name']
        product_price = stripe_sku['price']

        if bool(sku_metadata.get('discountable', False)) is True:
            if available_discount > 0 or comp_discount is True:
                if comp_discount is True:
                    product_price = 0
                    product_name += ' (discounted)'
                else:
                    if product_price <= available_discount:
                        product_price = 0
                        available_discount -= product_price
                        total_discount += product_price
                        product_name += ' (discounted)'
                    else:
                        total_discount += available_discount
                        product_price -= available_discount
                        available_discount = 0
                        product_name += ' (discounted)'

        line_items.append({
            'name': product_name,
            'amount': product_price,
            'currency': stripe_sku['currency'],
            'quantity': 1
        })
            
    return line_items


def create_checkout_session(request: Dict, line_items: Dict) -> Dict:
    metadata = {
        "name": request.get('name', None),
        "email": request.get('email', None),
        "skus": '|'.join(request.get('sku', [])),
        "company": request.get('company', None),
        "title": request.get('title', None),
        "experience": request.get('experience', None),
        "persona": request.get('persona', None),
        "country": request.get('country', None),
        "city": request.get('city', None),
        "mailing_list": request.get('mailing_list', False),
        "purchase_type": "event"
    }

    if request.get('dietary_restrictions', None) is not None:
        metadata['dietary_restrictions'] = '|'.join(request.get('dietary_restrictions', ''))

    if request.get('discount_code', None) is not None and request.get('discount_code', None) != '':
        metadata['discount_code'] = request.get('discount_code', None)

    sku = stripe.SKU.retrieve(
        request.get('sku')[0],
        api_key=os.environ["STRIPE_SECRET"]
    )
    product = stripe.Product.retrieve(
        sku['product'],
        api_key=os.environ["STRIPE_SECRET"]
    )

    metadata['event_id'] = product['id']

    company_name = request.get('company', None)
    if company_name is not None:
        metadata['company'] = company_name

    product_metadata = product.get('metadata', {})
    success_url = product_metadata.get('success_url', 'https://owasp.org/' + product_metadata.get('repo_name') + '/registration-success')
    cancel_url = product_metadata.get('cancel_url', 'https://owasp.org/' + product_metadata.get('repo_name') + '/registration-error')

    api_request = {
        "success_url": success_url,
        "cancel_url": cancel_url,
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(
        request.get('email')
    )
    if (stripe_customer_id is not None):
        api_request['customer'] = stripe_customer_id
    else:
        api_request['customer_email'] = request.get('email')

    api_request['payment_intent_data'] = {
        'metadata': metadata
    }

    api_request['line_items'] = line_items
    api_request['api_key'] = os.environ["STRIPE_SECRET"]
    api_response = stripe.checkout.Session.create(**api_request)

    return {
        'session_id': api_response['id']
    }


def is_order_comped(line_items):
    for line_item in line_items:
        if line_item['amount'] > 0:
            return False

    return True


def normalize_line_items(line_items):
    difference = 0
    for line_item in line_items:
        if line_item['amount'] == 0:
            line_item['amount'] = 100
            difference += 100

    for line_item in line_items:
        if line_item['amount'] > 100 and difference > 0:
            if line_item['amount'] - 100 >= difference:
                line_item['amount'] -= difference
                difference = 0
            else:
                difference -= line_item['amount'] - 100
                line_item['amount'] = 100
            if '(discounted)' not in line_item['name']:
                line_item['name'] += ' (discounted)'

    return line_items


def create_comp_order(request, line_items):
    metadata = {
        "name": request.get('name', None),
        "email": request.get('email', None),
        "skus": '|'.join(request.get('sku', [])),
        "company": request.get('company', None),
        "title": request.get('title', None),
        "experience": request.get('experience', None),
        "persona": request.get('persona', None),
        "country": request.get('country', None),
        "city": request.get('city', None),
        "mailing_list": request.get('mailing_list', False),
        "purchase_type": "event"
    }

    if request.get('dietary_restrictions', None) is not None:
        metadata['dietary_restrictions'] = '|'.join(request.get('dietary_restrictions', ''))

    if request.get('discount_code', None) is not None and request.get('discount_code', None) != '':
        metadata['discount_code'] = request.get('discount_code', None)

    sku = stripe.SKU.retrieve(
        request.get('sku')[0],
        api_key=os.environ["STRIPE_SECRET"]
    )
    product = stripe.Product.retrieve(
        sku['product'],
        api_key=os.environ["STRIPE_SECRET"]
    )
    product_metadata = product.get('metadata', {})

    metadata['event_id'] = product['id']

    company_name = request.get('company', None)
    if company_name is not None:
        metadata['company'] = company_name

    order_items = []
    order_total = 0
    inc = 0

    for line_item in line_items:
        sku = stripe.SKU.retrieve(
            request.get('sku')[inc],
            api_key=os.environ["STRIPE_SECRET"]
        )
        order_items.append({
            "amount": sku['price'],
            "currency": line_item['currency'],
            "description": line_item['name'],
            "parent": request.get('sku')[inc],
            "quantity": 1,
            "type": "sku"
        })
        order_total += sku['price']
        ++inc

    order_items.append({
        "amount": order_total * -1,
        "currency": product_metadata.get('currency', 'usd'),
        "description": 'Discount',
        "quantity": 1,
        "type": "discount"
    })

    stripe_customer_id = get_stripe_customer_id(
        request.get('email')
    )
    if (stripe_customer_id is None):
        customer_request = stripe.Customer.create(
            email=request.get('email'),
            name=request.get('name'),
            api_key=os.environ["STRIPE_SECRET"]
        )
        stripe_customer_id = customer_request['id']

    order = stripe.Order.create(
        currency=product_metadata.get('currency', 'usd'),
        customer=stripe_customer_id,
        metadata=metadata,
        items=order_items,
        api_key=os.environ["STRIPE_SECRET"]
    )

    success_url = product_metadata.get('success_url', 'https://owasp.org/' + product_metadata.get('repo_name') + '/registration-success')

    return_value = {
        'response_type': 'redirect',
        'redirect_url': success_url
    }

    return return_value


def return_response(response, success):
    if success:
        status_code = 200
        response = {
            "status": "OK",
            "data": response
        }
    else:
        status_code = 400
        response = {
            "status": "ERROR",
            "errors": response
        }

    return func.HttpResponse(
        body=json.dumps(response),
        status_code=status_code
    )


def get_stripe_customer_id(email):
    customers = stripe.Customer.list(
        email=email,
        api_key=os.environ["STRIPE_SECRET"]
    )
    if len(customers) > 0:
        for customer in customers:
            if customer.email == email:
                return customer.id

    return None
