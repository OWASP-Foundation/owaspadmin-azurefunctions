import logging
import json
import requests
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import spotchk
from ..SharedCode import helperfuncs
import base64
from urllib.parse import unquote_plus

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
    
    if not spotchk.spotchk().validate_query2(names):
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )

    gh = github.OWASPGitHub()
    respond_url = names['response_url']
    logging.info("Building staff projects and milestones json files")
    headers = {'content-type':'application/json'}
    data = {
         'response_type':'ephemeral',
         'text': 'Rebuilding staff projects and milestones...ignore timeouts'
     }

    # respond to caller...
    msg = json.dumps(data)
    r = requests.post(url = respond_url, headers=headers, data=msg)

    helperfuncs.build_staff_project_json(gh)
    
    return func.HttpResponse(f"Projects and milestones built!")
    
