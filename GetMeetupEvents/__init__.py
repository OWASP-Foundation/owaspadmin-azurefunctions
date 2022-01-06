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
                earliest = edate.strftime('%Y-%m-')+"01"

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



    # mu = OWASPMeetup()
    # if mu.Login():
    #     res = mu.GetGroupEvents('South-Florida-OWASP-Chapter',status='PAST',earliest='2021-10-01')
    #     event_json = json.loads(res)
    #     events = event_json['data']['proNetworkByUrlname']['eventsSearch']['edges']
    #     for event in events:            
    #         dt = datetime.strptime(event['node']['dateTime'][:10], '%Y-%m-%d')
    #         print(dt)
    # else:
    #     print("Could not log in.")