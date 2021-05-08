import logging

from requests.packages import urllib3

import azure.functions as func
import json
import stripe
import os
import re
import unicodedata
from datetime import datetime
from ..SharedCode import recurringtoken
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.copper import OWASPCopper

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
    customer_name = customer.get('name')
    if customer_name is None:
        errors = {
            'name': ['No first or last name.  Unable to auto-provision email']
        }
        return return_response(errors, False)
    metadata = customer.get('metadata', None)
    if metadata:
        owasp_email = metadata.get('owasp_email', None)
        if owasp_email:
            errors = {
                'email': ['Only one OWASP email address is allowed per member.']
            }
            return return_response(errors, False)
            
    first_name = customer_name.lower().strip().split(' ')[0]
    last_name = ''.join((customer_name.lower() + '').split(' ')[1:]).strip()
    nfn = unicodedata.normalize('NFD', first_name)
    nln = unicodedata.normalize('NFD', last_name)
    nfn = ''.join([c for c in nfn if not unicodedata.combining(c)])
    nln = ''.join([c for c in nln if not unicodedata.combining(c)])
    r2 = re.compile(r'[^a-zA-Z0-9]')
    first_name = r2.sub('',nfn)
    last_name = r2.sub('', nln)

    respb = True
    response = og.CreateSpecificEmailAddress(customer.get('email'), first_name, last_name, email, True)

    if 'Failed' in response:
        respb = False
    else:
        stripe.Customer.modify(
                            customer_id,
                            metadata={'owasp_email': email}
                        )
        oc = OWASPCopper()
        contact_json = oc.FindPersonByEmail(customer.get('email'))
        if contact_json != '':
            people = json.loads(contact_json)
            oc.UpdatePerson(people[0]['id'], other_email=email)

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