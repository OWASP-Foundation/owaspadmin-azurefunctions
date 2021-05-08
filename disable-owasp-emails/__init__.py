from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import Attachment
from sendgrid.helpers.mail import FileContent
from sendgrid.helpers.mail import FileName
from sendgrid.helpers.mail import FileType
from sendgrid.helpers.mail import Disposition

from sendgrid import SendGridAPIClient
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

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    # clean up metadata only
    setting = os.environ.get('Cleanup.Stripe.Meta', None)
    if setting is not None and setting == 'true':
        cleanup_customer_metadata()
        return
    
    # clean up metadata only
    setting = os.environ.get('Test.Copper', None)
    if setting is not None and setting == 'true':
        test_copper_logic()
        return

    #checking of owasp_email meta in Stripe not needed
    #stripe_owasp_emails = get_customers_from_stripe_export()
    #if len(stripe_owasp_emails) == 0:
    #    logging.error(
    #        "Did not load any emails for the leaders.  Aborting process.")
    #    return

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
                                #else:
                                    # not needed anymore - look for email in stripe owasp_email metadata
                                    #item = search_for_customer_email(
                                    #    stripe_owasp_emails, user_email)
                                    #if item != None:
                                    #    customers = stripe.Customer.list(
                                    #        email=item['Email'])
                                    #    if len(customers) > 0:
                                    #        saveEmail = should_email_be_removed(
                                    #            customers.data[0], notified_file)
                                    #        if(saveEmail):
                                    #            continue

                                remove_file.write(
                                    user['primaryEmail'] + "\n")
                                deleted_emails_count = deleted_emails_count + 1

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

    #SendResultsEmail(deleted_emails_count, errors_count)


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

def SendResultsEmail(deleted_emails_count, errors_count):
    try:
        message = Mail(
            from_email='noreply@owasp.org',
            to_emails='ccapellan@gmail.com',
            subject='Daily Email Cleanup, ' + \
                str(errors_count) + ' errors, ' + str(deleted_emails_count) + '  addresses disabled',
            html_content='<strong>Please find the results attached.</strong>')

        with open('save-email-stripe.txt', 'rb') as f:
            data = f.read()
            f.close()
        encoded_file = base64.b64encode(data).decode()
        attachedFile = Attachment(
            FileContent(encoded_file),
            FileName('save-email-stripe.txt'),
            FileType('application/txt'),
            Disposition('attachment')
        )
        message.attachment = attachedFile

        with open('save-email-leaders.txt', 'rb') as f:
            data = f.read()
            f.close()
        encoded_file = base64.b64encode(data).decode()
        attachedFile = Attachment(
            FileContent(encoded_file),
            FileName('save-email-leaders.txt'),
            FileType('application/txt'),
            Disposition('attachment')
        )
        message.attachment = attachedFile

        with open('delete-email.txt', 'rb') as f:
            data = f.read()
            f.close()
        encoded_file = base64.b64encode(data).decode()
        attachedFile = Attachment(
            FileContent(encoded_file),
            FileName('delete-email.txt'),
            FileType('application/txt'),
            Disposition('attachment')
        )
        message.attachment = attachedFile

        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
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

        # send 1 day notification
        if membership_notified == None:
            send_notification(customer, 1)
            notified_file.write(
                customer['email'] + '(1 day notification)' + "\n")
            stripe.Customer.modify(customer_id, metadata={
                "membership_notified": "true"},)
            stripe.Customer.modify(customer_id, metadata={
                "membership_notified_date": date.utcnow().strftime('%Y-%m-%d')},)
            stripe.Customer.modify(customer_id, metadata={
                "membership_last_notification": '1 day'},)
            return True

        membership_notified_date = metadata.get(
            'membership_notified_date', None)
        if membership_notified_date is None:
            logging.exception('membership_notified_date is empty for customer {customer_id}')
            return False
        notified_date = date.strptime(membership_notified_date, "%Y-%m-%d")
        days_sent = date.utcnow() - notified_date
        last_notification =  metadata.get(
            'membership_last_notification', None)

        # send >1 day notifications
        if days_sent.days >= 7 and last_notification is not '7 day':
            send_notification(customer, 7)
            stripe.Customer.modify(customer_id, metadata={
                "membership_last_notification": "7 day"},)
            notified_file.write(
                customer['email'] + '(7 day notification)' + "\n")
        elif days_sent.days >= 15 and last_notification is not '15 day':
            send_notification(customer, 15)
            stripe.Customer.modify(customer_id, metadata={
                "membership_last_notification": "15 day"},)
            notified_file.write(
                customer['email'] + '(15 day notification)' + "\n")
        elif days_sent.days >= 30:
            return False

        return True

    except Exception as ex:
        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        raise


def send_notification(customer, day):
    logging.info(f"send {day} notice to user with email: {customer['email']}")


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
                "membership_notified": "", "membership_notified_date": ""},)

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
                            not_in_copper_file.write(user['primaryEmail'] + "\n")
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

#not needed since we're not checking for owasp_email meta field in Stripe
#def get_customers_from_stripe_export():
#    try:
#        with open('customers.json') as f:
#            data = json.load(f)
#            return data

#    except Exception as ex:
#        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
#        message = template.format(type(ex).__name__, ex.args)
#        logging.exception(message)
#        raise
#
#def search_for_customer_email(customer_emails, email):
#    for item in customer_emails:
#        if item['owasp_email'] == email:
#            return item
#    return None