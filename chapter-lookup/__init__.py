import logging
import os
import azure.functions as func
import requests
import json
from ..SharedCode import salesforce

def main(req: func.HttpRequest, msg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    sf = salesforce.OWASPSalesforce()
    r = sf.Login()
    resString = "Usage: /chapter-lookup [Chapter Name]"
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
        msg.set(name)
        res = sf.FindChapter(name)
        
        return func.HttpResponse(res, status_code=200)
    else:
        return func.HttpResponse(
             resString,
             status_code=200
        )
