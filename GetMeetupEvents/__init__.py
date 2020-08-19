import logging
import json
import azure.functions as func
from ..SharedCode import meetup

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('GetMeetupEvents function processed a request.')

    name = req.params.get('group')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('group')

    if name:
        om = meetup.OWASPMeetup()
        if om.Login():
            result = om.GetGroupEvents(name)
            return func.HttpResponse(result)
        else:
            return func.HttpResponse('Group not found.', status_code = 400)
    else:
        return func.HttpResponse(
             "No group name provided",
             status_code=404
        )
