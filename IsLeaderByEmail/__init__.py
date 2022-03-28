import logging
import json
import os
import re
import azure.functions as func
from ..SharedCode.github import OWASPGitHub
import base64

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    email = req.params.get('email')
    if not email:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            email = req_body.get('email')

    if email:
        email = email.lower()
        gh = OWASPGitHub()
        r = gh.GetFile('owasp.github.io', '_data/leaders.json')
        if r.ok:
            doc = json.loads(r.text)
            content = base64.b64decode(doc['content']).decode(encoding='utf-8')
            leaders = json.loads(content)
            AddAdditionalLeaders(leaders)
            is_leader = False
            groups = []
            for leader in leaders:
                if email == leader['email']:
                    is_leader = True
                    groups.append(leader['group'])

            
            result = {
                'leader': is_leader,
                'groups': groups
            }

            return func.HttpResponse(body = json.dumps(result))
        else:
            error = {
                'error': 'Unable to verify.  Try again later.'
            }
            return func.HttpResponse(
                body=json.dumps(error),
                status_code=404
            )
    else:
        error = {
                'error': 'Missing required paramter - email'
            }
        return func.HttpResponse(
             body=json.dumps(error),
             status_code=404
        )

def AddAdditionalLeaders(leaders):
    addLeaders = json.loads(os.environ.get('OWASP.Additional.Leaders', '{ }'))
    leaders.extend(addLeaders)
