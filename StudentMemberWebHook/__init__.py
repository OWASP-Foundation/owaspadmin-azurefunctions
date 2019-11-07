import logging
import os
from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage

import azure.functions as func
from urllib.parse import unquote_plus
from ..SharedCode import wufoo
from ..SharedCode import salesforce
import base64

def main(req: func.HttpRequest, outputQueueItem: func.Out[func.QueueMessage]) -> func.HttpResponse:
    #return func.HttpResponse('Nothing to see here', status_code=400)
    logging.info('Student Membership webhook called')

    # determine information from passed in data
    # determine if/when 'paid' is marked

    firstname = lastname = email = member_type = country = postal_code = university = graduation_date = favorite_class = date_created = handshake = ''
    req_body = req.get_body()
    strbody = unquote_plus(req_body.decode("utf-8"))
    names = dict(x.split('=') for x in strbody.split('&'))
    
    wf = wufoo.OWASPWufoo()
    handshake = names.get(wf.HANDSHAKE_KEY_FIELD)
    if os.environ["WF_HANDSHAKE"] != handshake:
        return func.HttpResponse('Failed handshake', status_code = 400)
    
    
    firstname = names.get(wf.FIRST_NAME_FIELD)
    lastname = names.get(wf.LAST_NAME_FIELD)
    email = names.get(wf.EMAIL_FIELD)
    member_type = names.get(wf.MEMBERSHIP_TYPE_FIELD)
    country = names.get(wf.COUNTRY_FIELD)
    postal_code = names.get(wf.POSTAL_CODE_FIELD)
    university = names.get(wf.UNIVERSITY_FIELD)
    graduation_date = names.get(wf.GRADUATION_DATE_FIELD)
    favorite_class = names.get(wf.FAVORITE_CLASS_FIELD)
    date_created = names.get(wf.DATE_CREATED_FIELD)

    if firstname:
        
        #paid = wf.GetPaidField(os.environ['WF_STUDENT_FORM'], email, date_created)
        #if 'Completed' in paid:
        #    sf = salesforce.OWASPSalesforce()
            # do something cool with SF...
        #else: 

        # Just put it on a queue ... webhook is called BEFORE payment anyway...
        outputQueueItem.set(req.get_body())
            # put this on a queue to be looked at by timer function set for 5 minutes?  15 minutes?

        return func.HttpResponse("Ok")
    else:
        return func.HttpResponse(
             f"Invalid parameters in the request body: {req_body}",
             status_code=400
        )