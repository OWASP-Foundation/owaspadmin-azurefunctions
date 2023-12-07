import logging
import os
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user = None
    apikey = None
    try:
            req_body = req.get_json()
    except ValueError:
        pass
    else:
        user = req_body.get('user')
        apikey = req_body.get('apikey')

    if not user:
        user = req.params.get('user')    
    
    if not apikey:
         apikey = req.params.get('apikey')

    if not validate_apikey(user, apikey)
        return func.HttpResponse(
             "Could not be authenticated",
             status_code=401
        )
    
    return func.HttpResponse(f"We return nothing.")
    

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