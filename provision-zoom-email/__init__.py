import logging
import os
import azure.functions as func
import requests
import json
from ..SharedCode import salesforce
from ..SharedCode import spotchk
from urllib.parse import unquote_plus
import pathlib


def main(req: func.HttpRequest, pzmsg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    logging.info('provision zoom request.')  
    body = req.get_body()
    
    # validate the call...
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Call not valid (100)',
            status_code = 200
        )
    # convert url string parameters to dict
    names = dict(x.split('=') for x in strbody.split('&'))
    
    if not spotchk.spotchk().validate_query(names):
        return func.HttpResponse(
            'Call not valid (101)',
            status_code = 200
        )
    
    # convert dict to string
    jsonstr = json.dumps(names)
    # validation complete...let's do something...
    resp = 'Zoom Provisioning request received. You will receive a message when complete.' 
    
    #add this to the queue, it will be picked up by the provision-zoom-process function
    if 'provision-zoom' in names['command'] :
        pzmsg.set(jsonstr)
    
    headers = {"Content-Type":"application/json;charset=utf-8"}
    
    return func.HttpResponse(resp, headers=headers)
