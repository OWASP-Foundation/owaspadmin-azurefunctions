import logging
import os
import azure.functions as func
import requests
import json
from salesforce import *

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    sf = OWASPSalesforce()
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

    if name:
        res = sf.FindChapter(name)
        
        return func.HttpResponse(res, status_code=200)
    else:
        return func.HttpResponse(
             resString,
             status_code=400
        )
