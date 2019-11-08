import logging
import azure.functions as func
import json
from urllib.parse import unquote_plus

def main(req: func.HttpRequest, chmsg: func.Out[func.QueueMessage], prmsg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    logging.info('Slack Action Trigger')
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))
    jsonstr = strbody[strbody.find('=') + 1 :]
    #logging.info(jsonstr)

    resp = '{"response_action": "update","view": {"type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    #resp += strbody
    resp += 'Working on it, please wait..."} }]} }' 
    
    #add this to the queue, it will be picked up by the chapter-process function
    if 'Chapter' in jsonstr:
        chmsg.set(jsonstr)
    elif 'Project' in jsonstr:
        prmsg.set(jsonstr)

    headers = {"Content-Type":"application/json;charset=utf-8"}
    
    return func.HttpResponse(resp, headers=headers)

