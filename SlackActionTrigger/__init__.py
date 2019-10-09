import logging

import azure.functions as func
import json
from urllib.parse import unquote_plus

def main(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))
    jsonstr = strbody[strbody.find('=') + 1 :]
    logging.info(jsonstr)

    data = json.loads(jsonstr)
    resp = '{"response_action": "update","view": {"type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    #resp += strbody
    resp += ' And so an error occurred.  Chapter not completely created."} }]} }' 
    
    if data['type'] == 'view_submission':
        values = json_obj['view']['state']['values']
        resp = process_form(values)

    headers = {"Content-Type":"application/json;charset=utf-8"}
    logging.info('Slack Action Trigger')

    return func.HttpResponse(resp, headers=headers)

def process_form(values):
    chapter_name = values["cname-id"]["cname-value"]["value"]

    resp = '{"response_action": "update","view": {"type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    
    resp += chapter_name + ' Chapter created.'
    
    resp += '"} }]} }' 
    return resp