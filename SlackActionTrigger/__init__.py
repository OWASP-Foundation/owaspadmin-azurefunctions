import logging
import azure.functions as func
import json
from urllib.parse import unquote_plus
from ..EventsSlackbot.__init__ import main as event_bot

def main(req: func.HttpRequest,
         chmsg: func.Out[func.QueueMessage],
         prmsg: func.Out[func.QueueMessage],
         evtmsg: func.Out[func.QueueMessage]
         ) -> func.HttpResponse:
    logging.info('Slack Action Trigger')
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))
    jsonstr = strbody[strbody.find('=') + 1 :]
    #logging.info(jsonstr)

    # call event bot code if it is an interactive component related to events
    if is_event_action(jsonstr):
        return event_bot(req, evtmsg)

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


def is_event_action(jsonstr):
    event_actions = [
        'create_event',
        'list_event',
        'manage_event',
        'add_product',
        'list_products'
    ]
    
    return [action_name for action_name in event_actions if (action_name in jsonstr)]
