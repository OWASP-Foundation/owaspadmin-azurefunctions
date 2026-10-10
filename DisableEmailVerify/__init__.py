import logging

import azure.functions as func
import json
import base64
from ..SharedCode import OWASPGlueup

from ..SharedCode.github import OWASPGitHub
from ..SharedCode.owasp_web import OWASPWeb
from ..SharedCode.googleapi import OWASPGoogle
import SharedCode.helperfuncs as helperfuncs

from datetime import datetime, timezone

from azure.core.exceptions import ResourceNotFoundError
from ..SharedCode.azure_tables import get_email_notify_table_client


# DisableEmailVerify does the following:
# for each queue item:
#    if current membership not found for user:
#        if user not a leader:
#           if user not yet notified:
#               add email to DisableEmail15DayNoticeQueue
#            else if user notified >= 16 days ago:
#               add email to DisableOWASPEmail
#            else if user notified >= 15 days ago:
#               add email to DisableEmail1DayNoticeQueue
#           else if user notified >= 8 days ago:
#               add email to DisableEmail7DayNoticeQueue
def main(msg: func.QueueMessage, disableemail15daynoticequeue: func.Out[func.QueueMessage], disableemail7daynoticequeue: func.Out[func.QueueMessage], disableemail1daynoticequeue: func.Out[func.QueueMessage], disableowaspemailqueue: func.Out[func.QueueMessage]) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    
    data = json.loads(msg.get_body().decode('utf-8'))
    user_email = data.get('email', None)
    fullname = data.get('fullName', None)
    if not user_email:
        logging.warning("Email not found in queue message")
    
    # check if the user has a membership or if the user is a leader (even though we know all leaders are supposed to be members)
    if (not helperfuncs.membership_found(user_email)) and (not helperfuncs.is_leader(user_email)) and (not helperfuncs.is_ignore_email(user_email)):
        queues = {
            '15day': disableemail15daynoticequeue,
            '7day': disableemail7daynoticequeue,
            '1day': disableemail1daynoticequeue,
            '0day': disableowaspemailqueue
        }

        add_to_appropriate_queue(msg, user_email, fullname, queues)
    else:
        # this person is a member and maybe they became a member after being notified. Go ahead and delete any entry in the table for this user.        
        table_client = get_email_notify_table_client()
        try:      
            table_client.delete_entity("email_notify", user_email)
        except ResourceNotFoundError as exc:
            if getattr(exc, "error_code", None) != "EntityNotFound":
                raise
            pass # really not important if it exists or not
        
def add_to_appropriate_queue(msg, email, queues):
    # here is where we need to pull data from azure storage table to determine if they have been notified and when.  If they have not been notified, we will add them to the 15 day notice queue.  If they have been notified, we will check the date and add them to the appropriate queue based on how long ago they were notified.
    
    table_client = get_email_notify_table_client()

    try:
        entity = table_client.get_entity(
            partition_key="email_notify",
            row_key=email,
        )
    except ResourceNotFoundError as exc:
        if getattr(exc, "error_code", None) != "EntityNotFound":
            raise
        entity = None

    last_notification = entity.get('LastNotification') if entity else None
    if not last_notification: # case of user not notified
        # add to DisableEmail15DayNoticeQueue
        logging.info(f'adding {email} to 15 day notice queue')
        queues['15day'].set(json.dumps(msg))
    else:        
        
        notified_date = datetime.fromisoformat(last_notification)
        if notified_date.tzinfo is None:
            notified_date = notified_date.replace(tzinfo=timezone.utc)
        days_sent = datetime.now(timezone.utc) - notified_date

        if days_sent.days >= 8:
            logging.info(f'adding {email} to 7 day notice queue')
            queues['7day'].set(json.dumps(msg))
        elif days_sent.days >= 6:
            logging.info(f'adding {email} to 1 day notice queue')
            queues['1day'].set(json.dumps(msg))
        elif days_sent.days >= 1:
            logging.info(f'adding {email} to 0 day notice queue')
            queues['0day'].set(json.dumps(msg))
                
