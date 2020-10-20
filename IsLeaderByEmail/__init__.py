import logging
import json
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
            is_leader = False
            gleader = {'group_url':'', 'group':''}
            for leader in leaders:
                if email == leader['email']:
                    gleader = leader
                    is_leader = True
                    break
            return func.HttpResponse(f"{{'leader': {is_leader}, 'url':'{gleader['group_url']}', 'group':'{gleader['group']}'}}")
        else:
            return func.HttpResponse(
                "{'error': 'Unable to verify.  Try again later.'}",
                status_code=404
            )
    else:
        return func.HttpResponse(
             "{'error':'Missing required paramter - email'}",
             status_code=404
        )
