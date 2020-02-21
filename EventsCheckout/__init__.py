import logging

import azure.functions as func

import os
import json
import pathlib
from typing import Dict

import stripe

import urllib.parse

def main(req: func.HttpRequest) -> func.HttpResponse:
    request = req.get_json()
    errors = validate_request(request)

    if not bool(errors):
        response = create_checkout_session(request)
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

    if request.get('discount_code', None) is not None:
        try:
            coupon = stripe.Coupon.retrieve(
                request.get('discount_code').upper(),
                api_key=os.environ["STRIPE_TEST_SECRET"]
            )
            metadata = coupon.get('metadata', {})
            product = stripe.Product.retrieve(
                metadata.get('event_id'),
                api_key=os.environ["STRIPE_TEST_SECRET"]
            )
            sku = stripe.SKU.retrieve(
                request.get('sku'),
                api_key=os.environ["STRIPE_TEST_SECRET"]
            )
            sku_metadata = sku.get('metadata', {})
            if sku.get('product') != product['id'] or metadata.get('event_id') != product['id']:
                errors['discount_code'] = ['This discount is not valid']
        except Exception as err:
            errors['discount_code'] = ['This discount is not valid']

    return errors


def create_checkout_session(request: Dict) -> Dict:
    metadata = {
        "name": request.get('name', None),
        "email": request.get('email', None),
        "sku": request.get('sku', None),
        "discount_code": request.get('discount_code', None),
        "purchase_type": "event"
    }

    sku = stripe.SKU.retrieve(
        request.get('sku'),
        api_key=os.environ["STRIPE_TEST_SECRET"]
    )
    product = stripe.Product.retrieve(
        sku['product'],
        api_key=os.environ["STRIPE_TEST_SECRET"]
    )

    checkout_product_name = product.name + ' : ' + sku['attributes']['name']

    company_name = request.get('company', None)
    if company_name is not None:
        metadata['company'] = company_name

    api_request = {
        "success_url": "https://www2.owasp.org/www-event-example/registration-success",
        "cancel_url": "https://www2.owasp.org/www-event-example/registration-error",
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(
        request.get('email')
    )
    if (stripe_customer_id is not None):
        api_request['customer'] = stripe_customer_id
    else:
        api_request['customer_email'] = request.get('email')

    discount_code = request.get('discount_code', None)
    if discount_code is not None:
        coupon = stripe.Coupon.retrieve(
            request.get('discount_code').upper(),
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )
        checkout_product_name = checkout_product_name + ' + Discount'
        purchase_price = sku['price'] - coupon['amount_off']
    else:
        purchase_price = sku['price']

    api_request['payment_intent_data'] = {
        'metadata': metadata
    }

    api_request['line_items'] = [
        {
            'name': checkout_product_name,
            'amount': purchase_price,
            'currency': product['metadata']['currency'],
            'quantity': 1
        }
    ]

    api_request['api_key'] = os.environ["STRIPE_TEST_SECRET"]

    api_response = stripe.checkout.Session.create(**api_request)

    return {
        'session_id': api_response['id']
    }


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
        api_key=os.environ["STRIPE_TEST_SECRET"]
    )
    if len(customers) > 0:
        for customer in customers:
            if customer.email == email:
                return customer.id

    return None
