import logging
import os
import azure.functions as func
import json
import urllib.parse


def main(req: func.HttpRequest, msg: func.Out[func.QueueMessage]) -> func.HttpResponse:
    logging.info('project_create_jira request')
    
    post_data = req.get_body().decode("utf-8")
    post_dict = urllib.parse.parse_qs(post_data)

    token = post_dict.get('token')[0]

    if token != os.environ["SL_TOKEN_GENERAL"]:
        return func.HttpResponse(
            body='Invalid token',
            status_code=400
        )

    text = post_dict.get('text')[0]
    command = post_dict.get('command')[0]
    response_url = post_dict.get('response_url')[0]

    if command == '/project-create-jira':
        if '-' not in text:
            text = "NFRSD-" + text
        message = { "jira_id": text,
                "command": command,
                "response_url": response_url
            }
        msg.set(json.dumps(message))

    headers = {"Content-Type":"application/json;charset=utf-8"}
    return func.HttpResponse(
        body='Your request is queued and a response will be provided shortly.',
        status_code=200,
        headers=headers);
    