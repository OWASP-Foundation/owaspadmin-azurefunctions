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

    respond_url = names['response_url']

    thread = Thread(target=DelayedResponse, args = (respond_url,))
    thread.start()
    return func.HttpResponse(
            "Working on it...",
            status_code=200
    )


def DelayedResponse(args):
    # no parameters, just a simple rebuild-site
    gh = github.OWASPGitHub()
    r = gh.RebuildSite()
    resString = r.text
    headers = {"Accept":"application/json"}
    data = {
        "response_type":"ephemeral",
        "text": resString
    }
    r = requests.post(url = args, headers=headers, data=json.dumps(data))
    logging.info(r.text)
