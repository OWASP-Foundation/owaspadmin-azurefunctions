import logging
import azure.functions as func
import json
from urllib.parse import unquote_plus
from ..EventsSlackbot.__init__ import main as event_bot

def main(req: func.HttpRequest,
         chmsg: func.Out[func.QueueMessage],
         prmsg: func.Out[func.QueueMessage],
         evtmsg: func.Out[func.QueueMessage],
         cmmsg: func.Out[func.QueueMessage],
         evmsg: func.Out[func.QueueMessage]
         ) -> func.HttpResponse:
    logging.info('Slack Action Trigger')
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))
    jsonstr = strbody[strbody.find('=') + 1 :]
    #logging.info(jsonstr)

    resp = '{"response_action": "update","view": {"type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    #resp += strbody
    resp += 'Working on it, please wait..."} }]} }' 
    
    #add this to the queue, it will be picked up by the appropriate function
    if 'Chapter Name' in jsonstr:
        chmsg.set(jsonstr)
    elif 'Project Name' in jsonstr:
        prmsg.set(jsonstr)
    elif 'Committee Name' in jsonstr:
        cmmsg.set(jsonstr)
    elif 'Event Name' in jsonstr:
        evmsg.set(jsonstr)

    headers = {"Content-Type":"application/json;charset=utf-8"}
    
    return func.HttpResponse(resp, headers=headers)

