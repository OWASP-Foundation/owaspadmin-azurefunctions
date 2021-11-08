import logging

import azure.functions as func
import json
import base64
import os
import stripe
from ..SharedCode import copper

from ..SharedCode.github import OWASPGitHub
from ..SharedCode.googleapi import OWASPGoogle
from datetime import datetime

stripe.api_key = os.environ["STRIPE_SECRET"]

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
        logging.warn("Email not found in queue message")
    
    # check if they are in Copper
    if not membership_found(user_email) and not is_leader(user_email):
        # check if they are an active customer
        # could be an issue if casing isn't fixed
        customers = stripe.Customer.list(
            email=user_email)
        customer = None
        if customers is None or len(customers) <= 0:
                #add user to Stripe
            customer = stripe.Customer.create(email=user_email.lower(), 
                                                name=fullname)
        else:
            customer = customers.data[0]
    
        queues = {
            '15day': disableemail15daynoticequeue,
            '7day': disableemail7daynoticequeue,
            '1day': disableemail1daynoticequeue,
            '0day': disableowaspemailqueue
        }
        add_to_appropriate_queue(customer, user_email, fullname, queues)
    else:
        logging.info(f'User {user_email} is a member or leader')
def add_to_appropriate_queue(customer, email, fullName, queues):
    metadata = customer.get('metadata', None)
    customer_id = customer['id']
    msg = {
        'customer_id': customer_id,
        'email': email,
        'fullName': fullName
    }

    if not metadata or not metadata.get('membership_notified'): # case of user not notified
        # add to DisableEmail15DayNoticeQueue
        logging.info('adding {email} to 15 day notice queue')
        queues['15day'].set(json.dumps(msg))
    else:        
        membership_notified_date = metadata.get(
            'membership_notified_date', None)
        if membership_notified_date is None:
            logging.exception(f'membership_notified_date is empty for customer {customer_id}')
            return

        notified_date = datetime.strptime(membership_notified_date, "%Y-%m-%d")
        days_sent = datetime.utcnow() - notified_date
        last_notification = metadata.get(
            'membership_last_notification', None)

        if days_sent.days >= 1 and last_notification == '1 day':
            logging.info(f'adding {email} to 0 day notice queue')
            queues['0day'].set(json.dumps(msg))
        elif days_sent.days >= 6 and last_notification == '7 day':
            logging.info(f'adding {email} to 1 day notice queue')
            queues['1day'].set(json.dumps(msg))
        elif days_sent.days >= 8 and last_notification == '15 day':
            logging.info(f'adding {email} to 7 day notice queue')
            queues['7day'].set(json.dumps(msg))
        

def membership_found(email): # check copper for membership data and then Stripe, for good measure
    cp = copper.OWASPCopper()
    try:
        opp = cp.FindMemberOpportunity(email)
        if opp != None:
            return True
        else:
            customers = stripe.Customer.list(email=email)
            if customers is not None and len(customers) > 0:
                customer = customers.data[0]
                metadata = customer['metadata']
                membership_type = metadata.get('membership_type', None)

                # keep email if customer has a lifetime membership
                if membership_type != None and membership_type == 'lifetime':
                    logging.warn(f"Customer found with Stripe membership but no Copper membership: {email}")
                    return True

                membership_end = metadata.get('membership_end', None)
                memend_date = None
                if membership_end != None:
                    memend_date = datetime.strptime(membership_end, "%m/%d/%Y")

                # membership not expired, keep
                if memend_date != None and memend_date > datetime.utcnow():
                    logging.warn(f"Customer found with Stripe membership but no Copper membership: {email}")
                    return True            
                return False
    except Exception as ex:
        logging.exception(f"An exception of type {type(ex).__name__} occurred while processing a customer: {ex}")
        raise

def is_leader(email):
    leader_emails = get_leader_emails()
    if len(leader_emails) == 0:
        logging.error(
            "Did not load any emails for the leaders.  Aborting process.")
        return True # default to true because we could not get leader emails....

    return (email in leader_emails)

def get_leader_emails():
    try:
        gh = OWASPGitHub()
        gr = gh.GetFile('owasp.github.io', '_data/leaders.json')

        if gr.ok:
            doc = json.loads(gr.text)
            content = base64.b64decode(doc['content']).decode()
            data = json.loads(content)
            with open('/tmp/github-leaders-data.json', 'w') as outfile:
                json.dump(data, outfile)
        else:
            logging.error('Error retreiving leaders file from Github')
            return

        # extract emails and cleanse
        emails = []
        for leader in data:
            cleansed_email = leader['email'].replace('mailto://', '')
            cleansed_email = cleansed_email.replace('mailto:', '')
            cleansed_email = cleansed_email.lower()
            emails.append(cleansed_email)
        return emails
    except Exception as ex:
        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        raise

