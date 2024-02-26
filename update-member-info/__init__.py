import logging
import os
import jwt
from jwt import algorithms
import azure.functions as func
import requests
import json
import base64
from ..SharedCode import helperfuncs
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.copper import OWASPCopper
import stripe
from datetime import datetime

stripe.api_key = os.environ['STRIPE_SECRET']


def main(req: func.HttpRequest) -> func.HttpResponse:
    #LogIpFromRequestHeaders(req)
    
    token = req.params.get('authtoken')
    membership_data = None
    if not token:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            params = req_body.get('params')
            token = params.get('authtoken')
            membership_data = params.get('membership_data')
    
    if not membership_data:
        membership_data = json.loads(req.params.get('membership_data'))

    if token and membership_data:
        # do stuff here to decode the token and verify
        try:
            data = get_token_data(token)
        except Exception as err:
            logging.error(f'Invalid token: {err}')

        acl = json.loads(os.environ['MP_ACL'])
        if data and len(data) > 0: # WE USED TO ONLY ALLOW CERTAIN EMAILS BUT NOW ANY MEMBER EMAIL IS VALID...and ('owasp.org' in data['email'] or 'owasp.com' in data['email'] or data['email'] in acl['acl']): #only work with these email addresses
            #logging.info(f'Member data: {membership_data}')
            if not check_values(membership_data):
                return func.HttpResponse("invalid data", status_code=400)

            update_member_info(data['email'], membership_data)
            return func.HttpResponse(status_code=200)

    return func.HttpResponse(
            "bad request",
            status_code=400
    )

def check_values(membership_data):
    ret = True
    # data = {
    #         'name': person_data['name'],
    #         'address': person_data['address'],
    #         'phone_numbers': person_data['phone_numbers'],
    #         'emails': person_data['emails']            
    #     }
    name = membership_data.get('name',None)
    if not name or len(name) > 128:
        ret = False
    
    address = membership_data.get('address', None)
    if ret and not address:
        ret = False
    elif ret:
        street = address.get('street', None)
        city = address.get('city',None)
        postal_code = address.get('postal_code', None)
        country = address.get('country', None)
        if not street or not city or not postal_code or not country:
            ret = False
        else:
            if len(street) > 72 or len(city) > 72 or len(postal_code) > 72 or len(country) > 72:
                ret = False    
    if ret:
        emails = membership_data.get('emails', [])
        if len(emails) <= 0:
            ret = False
        else:
            for email in emails:
                addr = email.get('email', None)
                if not addr or len(addr) > 72:
                    ret = False
                    break
    
    if ret:
        phone_numbers = membership_data.get('phone_numbers', [])
        if len(phone_numbers)<= 0:
            ret = False
        else:
            for phone in phone_numbers:
                num = phone.get('number', None)
                if not num or len(num) > 72:
                    ret = False
                    break

    return ret

def get_public_keys():
    r = requests.get(os.environ['CF_TEAMS_DOMAIN'])
    public_keys = []
    jwk_set = r.json()
    for key_dict in jwk_set['keys']:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_dict))
        public_keys.append(public_key)
    return public_keys

def get_token_data(token):
    data = {}
    keys = get_public_keys()
    
    for key in keys:
        try:
            data = jwt.decode(token, key=key, audience=os.environ['CF_POLICY_AUD'], algorithms=['RS256'], verify=True)
            break
        except Exception as err:
            pass

    return data

def update_member_info(email, membership_data):
    cp = OWASPCopper()
    pjson = cp.FindPersonByEmail(email)
    if pjson and pjson != '':
        person = json.loads(pjson)
        pid = person[0]['id']
        res = cp.UpdatePersonInfo(pid, membership_data)
        if not res:
            logging.error(f"Failed to update {email}")
