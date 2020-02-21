import logging

import os
import json
import requests
import azure.functions as func
import urllib.parse

from ..SharedCode.eventbot.slack_request import SlackRequest

def main(req: func.HttpRequest, chmsg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    post_data = req.get_body().decode("utf-8")
    post_dict = urllib.parse.parse_qs(post_data)

    token = get_slack_token_from_payload(post_dict)

    logging.info(post_dict)

    if token != os.environ["SL_TOKEN"]:
        return func.HttpResponse(
            body='Invalid token',
            status_code=400
        )

    slack_request = SlackRequest(post_dict)
    processor = slack_request.get_processor()
    return processor.process(queue=chmsg)


def get_slack_token_from_payload(payload):
    if (payload.get('token', None)):
        return payload.get('token')[0]

    if (payload.get('payload', None)):
        payload_json = json.loads(payload.get('payload')[0])
        return payload_json["token"]

    return None
