import logging

import azure.functions as func
import base64
import requests
import os
import jwt
import json


def main(req: func.HttpRequest, mqueue: func.Out[func.QueueMessage]) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    
    if not validate_usage(req):
        logging.error('Failed login attempt')
        return func.HttpResponse("Not authorized.", status_code=403)    

    filej = req.params.get('file')
    if not filej:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            params = req_body.get('params')
            filej = params.get('file')

    if filej:
        f64part = filej[filej.find('base64,') + 7:]
        fstr = base64.b64decode(f64part).decode(encoding='utf-8')
        mqueue.set(fstr)
        return func.HttpResponse("File received.")
    else:
        logging.error("failed to get file from post")
        return func.HttpResponse(
             "Something is not right.",
             status_code=400
        )
def validate_usage(req):
    token = req.params.get('authtoken')
    allow_login = True
    if not token:
        try:
            req_body = req.get_json()
            params = req_body.get('params')
            token = params.get('authtoken')            
        except ValueError:
            pass

    try:
        data = get_token_data(token)
        if not data or len(data) == 0:      
            allow_login = False               
    except Exception as err:
        allow_login = False
        
    return allow_login

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
            data = jwt.decode(token, key=key, audience=os.environ['CF_ADMIN_POLICY_AUD'], algorithms=['RS256'], verify=True)
            break
        except Exception as err:
            pass

    return data