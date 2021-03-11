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

    invurl = "https://owasp.slack.com/api/users.admin.invite"
    data = {
        'email':email,
        'token': os.environ['SL_UINV_TOKEN'],
        'set_active': True
    }
    #headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN"]}' }

    # respond to caller...
    r = requests.post(url = invurl, data=data)
    
    return func.HttpResponse(r.text, status_code = r.status_code)
    