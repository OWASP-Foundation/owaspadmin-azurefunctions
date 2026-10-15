import datetime
import json
import logging

import azure.functions as func

from ..SharedCode import helperfuncs
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.glueup import OWASPGlueup
# this function goes through all Members and, if they are not found in Google Workspace as well using their membership email
# it queues the person for Email creation which is handled by AutoProvisionEmailProcess

def main(mytimer: func.TimerRequest, ape_queue: func.Out[func.QueueMessage]) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('AutoProvisionEmail Python timer trigger function ran at %s', utc_timestamp)

    gu = OWASPGlueup()
    members = gu.getMembers()    
    # iterate through all members
    if members:
        members = members.get('value')

    queue_list = []
    for member in members:
        user_email = member.get('emailAddress', None)
        fullname = member.get('givenName', '') + ' ' + member.get('familyName', '')

        
        if (user_email):
            # check to see if a Google Workspace account exists with the membership email
            # while it is possible that the person's membership email is not on the account, we assume that it SHOULD be
            goo = OWASPGoogle()
            # if the person doesn't exist in Google Workspace, add them to the AutoProvisionProcess queue            
            if goo.GetUser(user_email) == None:
                msg = {
                     'email' : user_email,
                     'fullName' : fullname
                 }
                queue_list.append(msg)                
        else:
            logging.info(f"No user email found for member {fullname}")
            
        if len(queue_list) > 0:
            ape_queue.set(json.dumps(msg))