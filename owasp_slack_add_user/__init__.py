import logging

import azure.functions as func
import requests
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    email = req.params.get('email')
    if not email:
        request = req.get_json()
        email = request.get('email', None)
    
    invurl = req.params.get('invurl')
    if not invurl:
        invurl = "https://owasp.slack.com/api/users.admin.invite"
    
    token = req.params.get('sltoken')
    if not token:
        token = os.environ['SL_UINV_TOKEN']
        
    data = {
        'email':email,
        'token': token,
        'set_active': True
    }
    #headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN"]}' }

    # respond to caller...
    r = requests.post(url = invurl, data=data)
    
    return func.HttpResponse(r.text, status_code = r.status_code)
    