import logging
import os
import azure.functions as func
import requests
import json
from ..SharedCode import salesforce
from ..SharedCode import spotchk
from urllib.parse import unquote_plus

def main(req: func.HttpRequest, msg: func.Out[func.QueueMessage]) -> func.HttpResponse:

    # first check for a valid call
    body = req.get_body()
    
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Contact not found (100)',
            status_code = 200
        )

    names = dict(x.split('=') for x in strbody.split('&'))
    
    if not spotchk.spotchk().validate_query(names):
        return func.HttpResponse(
            'Contact not found (101)',
            status_code = 200
        )

    sf = salesforce.OWASPSalesforce()
    r = sf.Login()
    resString = "Usage: /contact-lookup [Contact Name]"
    if not sf.TestResultCode(r.status_code):
        return func.HttpResponse(
            "Failed to login to Salesforce",
            status_code = r.status_code
        )

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')


    if not name:
        name = req.params.get('text')
    if not name:
        body = req.get_body()
        strbody = body.decode("utf-8")
        names = dict(x.split('=') for x in strbody.split('&'))
        name = names['text']


    if name:
        logging.info("adding parameter to queue")
        msg.set(name)
        res = sf.FindContact(name)
        
        return func.HttpResponse(res, status_code=200)
    else:
        return func.HttpResponse(
             resString,
             status_code=200
        )
