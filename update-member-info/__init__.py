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
    if not token:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            token = req_body.get('authtoken')
    membership_data = req.params.get('membership_data')
    if not membership_data:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            membership_data = json.loads(req_body.get('membership_data'))

    if token and membership_data:
        # do stuff here to decode the token and verify
        try:
            data = get_token_data(token)
        except Exception as err:
            logging.error(f'Invalid token: {err}')

    if data and len(data) > 0 and 'owasp.com' in data['email']: #only work with this email address for now
        logging.info(f'Member data: {membership_data}')
        update_member_info(data['email'], membership_data)
        return func.HttpResponse(status_code=200)
    else:
        return func.HttpResponse(
             "malformed request",
             status_code=404
        )

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
