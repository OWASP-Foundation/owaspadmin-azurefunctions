import logging
import json
import datetime

import azure.functions as func
from ..SharedCode import meetup

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('GetMeetupEvents function processed a request.')

    name = req.params.get('group')
    status = req.params.get('status')
    earliest = ''
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('group')
            status = req_body.get('status')
            if not status:
                status = 'upcoming'
            if status == 'past':
                edate = datetime.datetime.today() + datetime.timedelta(-30)
                earliest = edate.strftime('%Y-%m-')+"01T00:00:00.000"

    if name:
        om = meetup.OWASPMeetup()
        if om.Login():
            result = om.GetGroupEvents(name, earliest, status)
            return func.HttpResponse(result)
        else:
            return func.HttpResponse('Group not found.', status_code = 400)
    else:
        return func.HttpResponse(
             "No group name provided",
             status_code=404
        )
