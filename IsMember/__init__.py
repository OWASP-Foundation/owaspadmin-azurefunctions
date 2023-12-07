import logging
import os
import json
import azure.functions as func
from ..SharedCode.copper import OWASPCopper

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user = None
    apikey = None
    member_email = None
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        user = req_body.get('user')
        apikey = req_body.get('apikey')
        member_email = req_body.get('email')

    if not user:
        user = req.params.get('user')    
    
    if not apikey:
         apikey = req.params.get('apikey')

    if not member_email:
        member_email = req.params.get('email')

    if not validate_apikey(user, apikey):
        return func.HttpResponse(
             "Could not be authenticated",
             status_code=401
        )
    
    return validate_member(member_email)
        
def validate_apikey(user, apikey):
    result = False
    valid_keys = os.environ.get('MEMBER_API_KEYS', None)
    if valid_keys:
        for key in valid_keys:
             if key.get('user', None):
                  if key.get('apikey', None) == apikey:
                       msg = f"User {user} accessed the api."
                       logging.info(msg)
                       result = True
                       break

    return result

def validate_member(member_email):
    msg = "User not found"
    code = 404

    cp = OWASPCopper()
    opptxt = cp.FindMemberOpportunity(member_email)
    if opptxt != None and 'Error:' not in opptxt:
        msg = "User found"
        code = 200

    return func.HttpResponse(msg, code)