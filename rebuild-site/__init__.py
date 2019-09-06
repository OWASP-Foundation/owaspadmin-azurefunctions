import logging
import os
import requests
import json
from threading import Thread

import azure.functions as func
from ..SharedCode import github
from ..SharedCode import spotchk

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    remote = req.params.get('remote')
    
    # first check for a valid call
    body = req.get_body()
    strbody = body.decode("utf-8")
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

    # Workaround for not supported threaded operation
    # When first called, remote will not exist and this func will make another rebuild-site call to finish the job
    if not remote or remote == "true":
        try:
            requests.post("https://owaspadmin.azurewebsites.net/api/rebuild-site?remote=false",timeout=0.0000000001, data=body)
        except requests.exceptions.ReadTimeout: 
            pass

        return func.HttpResponse(
            "Working on it...",
            status_code = 200
        )
    # Do the work that may take more than the timeout....
    gh = github.OWASPGitHub()
    r = gh.RebuildSite()
    resString = r.text
    headers = {"content-type":"application/json"}
    data = {
         "response_type":"ephemeral",
         "text": resString
     }

    respond_url = names["response_url"]
    # respond to caller...
    r = requests.post(url = respond_url, headers=headers, data=json.dumps(data))
    
    return func.HttpResponse(
            "This string is going to a caller who isn't listening...",
            status_code=200
    )