import logging
import os
import azure.functions as func
import requests
import json
from ..SharedCode import salesforce
from ..SharedCode import spotchk
from urllib.parse import unquote_plus
import pathlib


def main(req: func.HttpRequest, rpmsg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    logging.info('chapter-report request')
    
    body = req.get_body()
    
    # validate the call...
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Call not valid (100)',
            status_code = 200
        )
    names = dict(x.split('=') for x in strbody.split('&'))
    
    if not spotchk.spotchk().validate_query(names):
        return func.HttpResponse(
            'Call not valid (101)',
            status_code = 200
        )
    # validation complete...let's do something...
    resp = '{"response_action": "update","view": {"type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    #resp += strbody
    resp += 'Report request received. You will receive a message when available."} }]} }' 
    
    #add this to the queue, it will be picked up by the chapter-process function
    if 'chapter-report' in jsonstr:
        rpmsg.set(jsonstr)
    
    headers = {"Content-Type":"application/json;charset=utf-8"}
    
    return func.HttpResponse(resp, headers=headers)
