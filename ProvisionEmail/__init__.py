import logging
from urllib.parse import unquote_plus

from requests.packages import urllib3

from SharedCode import spotchk
import azure.functions as func
import json
import os
import re
import unicodedata
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From
from datetime import datetime
from ..SharedCode import recurringtoken
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.glueup import OWASPGlueup
from SharedCode import googleapi

def main(req: func.HttpRequest, pemsg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    logging.info('provision email request.')  

    if not validate_call(req):
        return func.HttpResponse('Call not valid (100)', status_code=400)
    # validation complete...let's do something...
    
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))    
    names = dict(x.split('=') for x in strbody.split('&'))

     # convert dict to string
    jsonstr = json.dumps(names)
    # validation complete...let's do something...
    resp = 'Email Provisioning request received. You will receive a message when complete.' 
    
    #add this to the queue, it will be picked up by the provision-zoom-process function
    if 'provision-email' in names['command'] :
        pemsg.set(jsonstr)
    
    headers = {"Content-Type":"application/json;charset=utf-8"}
    
    return func.HttpResponse(resp, headers=headers)
    
def validate_call(req: func.HttpRequest) -> bool:
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return False
    names = dict(x.split('=') for x in strbody.split('&'))
    if not spotchk.spotchk().validate_query2(names):
        return False

    if not 'command' in names or not 'provision-email' in names['command']:
        return False
    
    return True