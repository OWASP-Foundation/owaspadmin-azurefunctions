import logging
import os
import requests
import json
from urllib.parse import unquote_plus

import azure.functions as func
from ..SharedCode import github
from ..SharedCode import spotchk

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    # first check for a valid call
    body = req.get_body()
    
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )

    names = dict(x.split('=') for x in strbody.split('&'))
    
    if not spotchk.spotchk().validate_query(names):
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )
    
    logging.info('Requesting rebuild from Github...')
    # Do the work that may take more than the timeout....
    gh = github.OWASPGitHub()
    r = gh.RebuildSite()
    if gh.TestResultCode(r.status_code):
        resString = "Build queued..."
    else:
        resString = r.text

    headers = {'content-type':'application/json'}
    data = {
         'response_type':'ephemeral',
         'text': resString
     }

    respond_url = names['response_url']
    # respond to caller...
    msg = json.dumps(data)
    r = requests.post(url = respond_url, headers=headers, data=msg)
     

    return func.HttpResponse()