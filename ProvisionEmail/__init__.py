import logging

from requests.packages import urllib3

import azure.functions as func
import json
import stripe
import os
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

    if email is None:
        errors = {
            'email': ['Email is required']
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
    response = og.CreateSpecificEmailAddress(customer.get('email'), first_name, last_name, email, True)

    if 'Failed' in response:
        respb = False
    else:
        stripe.Customer.modify(
                            customer_id,
                            metadata={'owasp_email': email}
                        )
    return return_response(response, respb)

def return_response(response_str, success):
    if success:
        status_code = 200
        response = {
            "status": "OK",
            "data": response_str
        }
    else:
        status_code = 400
        response = {
            "status": "ERROR",
            "errors": response_str
        }
    
    return func.HttpResponse(
        body=json.dumps(response),
        status_code=status_code
    )