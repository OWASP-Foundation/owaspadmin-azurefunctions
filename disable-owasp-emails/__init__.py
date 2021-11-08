from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import Attachment
from sendgrid.helpers.mail import FileContent
from sendgrid.helpers.mail import FileName
from sendgrid.helpers.mail import FileType
from sendgrid.helpers.mail import Disposition

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From

from ..SharedCode.github import OWASPGitHub
from ..SharedCode.googleapi import OWASPGoogle
import datetime
from datetime import datetime
from datetime import timezone
import logging
import azure.functions as func
import json
import base64
import os
import stripe
from ..SharedCode import copper

stripe.api_key = os.environ["STRIPE_SECRET"]
cp = copper.OWASPCopper()

# This function will be run every day at 4 a.m. CST (9 a.m. UTC)
# timer function to kick off the process which checks google emails and verifies that the person with the email is either:
#    * An OWASP Member
#    * An OWASP Leader
# if either of those two cases is not true, the email will get flagged for suspension after 15 days
# this function works in conjunction with these other Azure functions:
#    DisableEmailVerify
#    DisableEmail15DayNotice
#    DisableEmail7DayNotice
#    DisableEmail1DayNotice
#    DisableOWASPEmail
#
# Workflow as follows:
# for each active google user:
#    get primary email address
#    if the email address is not in the list of ignored emails and the email was created > 7 days ago (give some time to allow for linking of the email to a valid OWASP membership email - should be automatic but better too for emails created specifically for administrative uses, etc)
#        add email to DisableEmailVerifyQueue
#
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
#
# DisableEmail15DayNotice:
# for each queue item:
#    send 15 day notice
#    update user metadata
# 
# DisableEmail7DayNotice does:
# for each queue item:
#    send 7 day notice
#    update user metadata
# 
# DisableEmail7DayNotice does:
# for each queue item:
#    send 7 day notice
#    update user metadata


def main(mytimer: func.TimerRequest, disableemailverifyqueue: func.Out[func.QueueMessage]) -> None:
    
    utc_timestamp = datetime.utcnow().replace(
        tzinfo=timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger for disable-owasp-emails function ran at %s', utc_timestamp)

    # clean up metadata only
    setting = os.environ.get('Disable.OWASP.Emails.Cleanup.Stripe.Meta', None)
    if setting is not None and setting == 'true':
        cleanup_customer_metadata()
        return

    # clean up metadata only
    setting = os.environ.get('Disable.OWASP.Emails.Test.Copper', None)
    if setting is not None and setting == 'true':
        test_copper_logic()
        return

    emails_to_ignore = os.environ.get('Disable.OWASP.Emails.Ignore.Emails', None).replace(' ','').split(',')

    test_mode = os.environ.get('Disable.OWASP.Emails.Test.Mode', 'true')
    test_users = [
        'ulysses.one.suspender@owasp.org', 
        'ulysses.two.suspender@owasp.org',
        'ulysses.three.suspender@owasp.org',
        'ulysses.four.suspender@owasp.org',
        'ulysses.five.suspender@owasp.org'
        ]

    try:
        og = OWASPGoogle()
        next_page_token = None
        errors_count = 0

        while True:
            google_users = og.GetActiveUsers(next_page_token)
            next_page_token = google_users.get('nextPageToken')
            for user in google_users['users']:
                try:
                    user_email = user['primaryEmail'].lower()

                    #test logic
                    if  test_mode == 'true' and user_email not in test_users:
                        continue
                    
                    #skip emails that should be ignored
                    if user_email in emails_to_ignore:
                        continue
                    created = datetime.strptime(user['creationTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    if (datetime.today() - created).days < 7:
                        continue
    
                    msg = {
                        'customer_id': -1,
                        'email': user_email,
                        'fullName': user['name']['fullName']
                    }

                    logging.info(f'Adding {user_email} to verify queue')
                    disableemailverifyqueue.set(json.dumps(msg))

                except Exception as ex:
                    template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
                    message = template.format(
                        type(ex).__name__, ex.args)
                    logging.error(message)
                    errors_count = errors_count + 1
            
            if not next_page_token:
                break

    except Exception as ex:
        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        raise

def cleanup_customer_metadata():
    customers = stripe.Customer.list(limit=100)
    for customer in customers.auto_paging_iter():
        metadata = customer['metadata']
        membership_notified = metadata.get('membership_notified', None)
        if membership_notified is not None:
            stripe.Customer.modify(customer['id'], metadata={
                "membership_notified": "", "membership_notified_date": "", "membership_last_notification": ""},)


def test_copper_logic():
    with open('/tmp/email-found-in-copper.txt', 'w') as in_copper_file:
        with open('/tmp/email-not-in-copper.txt', 'w') as not_in_copper_file:
            try:
                og = OWASPGoogle()
                cp = copper.OWASPCopper()
                next_page_token = None

                while True:
                    google_users = og.GetActiveUsers(next_page_token)

                    for user in google_users['users']:
                        user_email = user['primaryEmail'].lower()

                        # check if they are in Copper
                        if(email_found_with_copper(user_email)):
                            in_copper_file.write(user['primaryEmail'] + "\n")
                        else:
                            not_in_copper_file.write(
                                user['primaryEmail'] + "\n")
                    next_page_token = google_users.get('nextPageToken')
                    if not next_page_token:
                        break
            except Exception as ex:
                template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logging.exception(message)
                raise
        in_copper_file.close()
    not_in_copper_file.close()
