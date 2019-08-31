import logging
import os
import azure.functions as func
import requests
import json


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    sf_consumer_key = os.environ["SF_CONSUMER_KEY"]
    sf_consumer_secret = os.environ["SF_CONSUMER_SECRET"]
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        session = requests.Session()
        
        return func.HttpResponse("You requested info on " + name)
    else:
        return func.HttpResponse(
             "Usage: /chapter-lookup [Chapter Name]",
             status_code=400
        )
