import logging

import azure.functions as func

import os
import json
import pathlib
from typing import Dict

import stripe
stripe.api_key = os.environ["STRIPE_TEST_SECRET"]

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

    return errors


def create_checkout_session(request: Dict) -> Dict:
    metadata = {
        "name": request.get('name', None),
        "email": request.get('email', None),
        "sku": request.get('sku', None),
        "purchase_type": "event"
    }

    sku = stripe.SKU.retrieve(request.get('sku'))
    product = stripe.Product.retrieve(sku['product'])

    checkout_product_name = product.name + ' : ' + sku['attributes']['name']

    company_name = request.get('company', None)
    if company_name is not None:
        metadata['company'] = company_name

    api_request = {
        "success_url": "https://www2.owasp.org/www-event-example/registration-success",
        "cancel_url": "https://www2.owasp.org/www-event-example/registration-error",
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(request.get('email'))
    if (stripe_customer_id is not None):
        api_request['customer'] = stripe_customer_id
    else:
        api_request['customer_email'] = request.get('email')

    api_request['payment_intent_data'] = {
        'metadata': metadata
    }

    api_request['line_items'] = [
        {
            'name': checkout_product_name,
            'amount': sku['price'],
            'currency': product['metadata']['currency'],
            'quantity': 1
        }
    ]

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
    customers = stripe.Customer.list(email=email)
    if len(customers) > 0:
        for customer in customers:
            if customer.email == email:
                return customer.id

    return None
