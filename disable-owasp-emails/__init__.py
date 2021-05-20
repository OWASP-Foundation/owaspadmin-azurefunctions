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
from datetime import datetime as date
import logging
import azure.functions as func
import json
import base64
import os
import stripe
from ..SharedCode import copper

stripe.api_key = os.environ["STRIPE_SECRET"]
cp = copper.OWASPCopper()

def main(mytimer: func.TimerRequest) -> None:
    
    utc_timestamp = date.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

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

    test_mode = os.environ.get('Disable.OWASP.Emails.Test.Mode', False)
    test_users = [
        'ulysses.one.suspender@owasp.org', 
        'ulysses.two.suspender@owasp.org',
        'ulysses.three.suspender@owasp.org',
        'ulysses.four.suspender@owasp.org',
        'ulysses.five.suspender@owasp.org'
        ]

    leader_emails = get_leader_emails()
    if len(leader_emails) == 0:
        logging.error(
            "Did not load any emails for the leaders.  Aborting process.")
        return

    deleted_emails_count = 0

    try:
        og = OWASPGoogle()
        cp = copper.OWASPCopper()
        next_page_token = None

        count = 0
        errors_count = 0

        with open('save-email-leaders.txt', 'w') as save_leaders_file:
            with open('owasp-email-removed.txt', 'w') as remove_file:
                with open('notified-users.txt', 'w') as notified_file:
                    while True:
                        google_users = og.GetActiveUsers(next_page_token)
                        for user in google_users['users']:
                            try:
                                user_email = user['primaryEmail'].lower()

                                #test logic
                                if  test_mode == 'true' and user_email not in test_users:
                                    continue
                                
                                # check if they are in Copper
                                if(email_found_with_copper(user_email)):
                                    save_leaders_file.write(
                                        user['primaryEmail'] + ' (in copper)' + "\n")
                                    continue

                                # check if they are an active leader
                                if user_email in leader_emails:
                                    save_leaders_file.write(
                                        user['primaryEmail'] + ' (in leaders file)' + "\n")
                                    continue

                                # check if they are an active customer
                                # could be an issue if casing isn't fixed
                                customers = stripe.Customer.list(
                                    email=user_email)
                                if customers is not None and len(customers) > 0:
                                    saveEmail = should_email_be_removed(
                                        customers.data[0], notified_file)
                                    if(saveEmail):
                                        continue
                                    else:
                                        og.SuspendUser(user['primaryEmail'])
                                        remove_file.write(
                                            user['primaryEmail'] + "\n")
                                        deleted_emails_count = deleted_emails_count + 1
                                else:
                                    add_user_to_stripe_and_notify(user_email, user['name']['fullName'], notified_file)
                            except Exception as ex:
                                template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
                                message = template.format(
                                    type(ex).__name__, ex.args)
                                logging.error(message)
                                errors_count = errors_count + 1

                        next_page_token = google_users.get('nextPageToken')
                        if not next_page_token:
                            break
                notified_file.close()
            remove_file.close()
        save_leaders_file.close()
    except Exception as ex:
        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        raise


def get_leader_emails():
    try:
        gh = OWASPGitHub()
        gr = gh.GetFile('owasp.github.io', '_data/leaders.json')

        if gr.ok:
            doc = json.loads(gr.text)
            content = base64.b64decode(doc['content']).decode()
            data = json.loads(content)
            with open('github-leaders-data.json', 'w') as outfile:
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


def should_email_be_removed(customer, notified_file):
    try:
        metadata = customer['metadata']
        membership_type = metadata.get('membership_type', None)

        # keep email if customer has a lifetime membership
        if membership_type != None and membership_type == 'lifetime':
            logging.info(
                f"keeping lifetime user with email: {customer['email']}")
            return True

        membership_end = metadata.get('membership_end', None)
        if membership_end != None:
            memend_date = date.strptime(membership_end, "%m/%d/%Y")

            # membership not expired
            if memend_date != None and memend_date > date.utcnow():
                return True

        membership_notified = metadata.get('membership_notified', None)
        customer_id = customer['id']

        # send 15 day notification
        if membership_notified == None:
            notification_sent = send_notification(customer['email'], 15)
            if notification_sent:
                notified_file.write(
                    customer['email'] + '(15 day notification)' + "\n")
                stripe.Customer.modify(customer_id, metadata={
                    "membership_notified": "true"},)
                stripe.Customer.modify(customer_id, metadata={
                    "membership_notified_date": date.utcnow().strftime('%Y-%m-%d')},)
                stripe.Customer.modify(customer_id, metadata={
                    "membership_last_notification": '15 day'},)
            else:
                 notified_file.write(
                    customer['email'] + '- notification could not be sent' + "\n")
            return True

        membership_notified_date = metadata.get(
            'membership_notified_date', None)
        if membership_notified_date is None:
            logging.exception(
                'membership_notified_date is empty for customer {customer_id}')
            return False
        notified_date = date.strptime(membership_notified_date, "%Y-%m-%d")
        days_sent = date.utcnow() - notified_date
        last_notification = metadata.get(
            'membership_last_notification', None)

        # send >7 day notifications
        if days_sent.days >= 7 and last_notification == '15 day':
            send_notification(customer['email'], 7)
            stripe.Customer.modify(customer_id, metadata={
                "membership_last_notification": "7 day"},)
            notified_file.write(
                customer['email'] + '(7 day notification)' + "\n")

        elif days_sent.days >= 15 and last_notification == '7 day':
            send_notification(customer['email'], 1)
            stripe.Customer.modify(customer_id, metadata={
                "membership_last_notification": "1 day"},)
            notified_file.write(
                customer['email'] + '(1 day notification)' + "\n")
        
        elif days_sent.days >= 15 and last_notification == '1 day':
            return False

        return True

    except Exception as ex:
        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        raise


def add_user_to_stripe_and_notify(email, fullname, notified_file):
    #add user to Stripe
    customer_request = stripe.Customer.create(email=email.lower(), 
                                                  name=fullname,
                                                  api_key=os.environ["STRIPE_SECRET"]
                                                )

    #send notification
    notification_sent = send_notification(email, 15)
    if notification_sent:
        notified_file.write(
            email + '(15 day notification)' + "\n")
        stripe.Customer.modify(customer_request['id'], metadata={
            "membership_notified": "true"},)
        stripe.Customer.modify(customer_request['id'], metadata={
            "membership_notified_date": date.utcnow().strftime('%Y-%m-%d')},)
        stripe.Customer.modify(customer_request['id'], metadata={
            "membership_last_notification": '15 day'},)
    else:
            notified_file.write(
            email + '- notification could not be sent' + "\n")
    return


def send_notification(user_email, day):
    template_id = None
    if day == 1:
        template_id = os.environ.get('SG_MEMBER_TEMPLATE_1_DAY')
    elif day == 7:
        template_id = os.environ.get('SG_MEMBER_TEMPLATE_7_DAY')
    elif day == 15:
        template_id = os.environ.get('SG_MEMBER_TEMPLATE_15_DAY')
    else:
        logging.exception('SendGrid message not found')
        return False
    
    message = Mail(
        from_email=From('noreply@owasp.org', 'OWASP'),
        to_emails=user_email,
        html_content='<strong>Email Removal</strong>')
    message.template_id = template_id
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
        return True
    except Exception as ex:
        template = "An exception of type {0} occurred while sending an email. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        return False


def email_found_with_copper(email):
    try:
        opp = cp.FindMemberOpportunity(email)
        if opp != None:
            print(f'Copper found membership for {email}')
            return True
        else:
            print(f'No membership found in Copper for {email}')
            return False
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
    with open('email-found-in-copper.txt', 'w') as in_copper_file:
        with open('email-not-in-copper.txt', 'w') as not_in_copper_file:
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
