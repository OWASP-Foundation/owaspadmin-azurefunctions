import logging

import azure.functions as func
import json
import stripe
from datetime import datetime
from ..SharedCode import recurringtoken
from ..SharedCode.googleapi import OWASPGoogle

def main(req: func.HttpRequest) -> func.HttpResponse:
    request = req.get_json()

    token = request.get('token', None)
    email = request.get('email', None)
    if token is None:
        errors = {
            'token': ['token is required']
        }
        return return_response(errors, False)

    customer_id = recurringtoken.decode_token(token)
    customer = stripe.Customer.retrieve(
        customer_id
    )
    metadata = customer.get('metadata', {})
    og = OWASPGoogle()
    first_name = customer.get('name')
    last_name = customer.get('name')
    respb = True
    response = og.CreateEmailAddress(customer.get('email'), first_name, last_name, True)
    if 'Failed' in response:
        respb = False
        
    return_response(response, respb)

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