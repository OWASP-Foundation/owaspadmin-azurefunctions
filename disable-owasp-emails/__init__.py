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
import logging
import azure.functions as func
import json
import base64
import os
import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    leader_emails = get_leader_emails()
    if len(leader_emails) == 0:
        logging.error(
            "Did not load any emails for the leaders.  Aborting process.")
        return

    deleted_emails_count = 0
    errors_count = 0

    try:
        og = OWASPGoogle()
        next_page_token = None
        with open('save-email-stripe.txt', 'w') as save_stripe_file:
            with open('save-email-leaders.txt', 'w') as save_leaders_file:
                with open('delete-email.txt', 'w') as remove_file:
                    while True:
                        google_users = og.GetActiveUsers(next_page_token)
                        for user in google_users['users']:
                            try:
                                # check if they are an active leader
                                if user['primaryEmail'].lower() in leader_emails:
                                    save_leaders_file.write(
                                        user['primaryEmail'] + "\n")
                                    continue

                                # check if they are an active customer
                                # could be an issue until casing is fixed
                                customer = stripe.Customer.list(
                                    email=user['primaryEmail'])
                                if len(customer) > 0:
                                    save_stripe_file.write(
                                        user['primaryEmail'] + "\n")
                                    continue

                                remove_file.write(user['primaryEmail'] + "\n")
                                deleted_emails_count = deleted_emails_count + 1

                            except:
                                logging.error("error processing user; continuing to next user")
                                errors_count = errors_count + 1

                        next_page_token = google_users.get('nextPageToken')
                        if not next_page_token:
                            break

                remove_file.close()
            save_leaders_file.close()
        save_stripe_file.close()
    except:
        logging.exception('Unexpected error:')
        raise

    SendResultsEmail(deleted_emails_count, errors_count)

def get_leader_emails():
    try:
        gh = OWASPGitHub()
        gr = gh.GetFile('owasp.github.io', '_data/leaders.json')

        if gr.ok:
            doc = json.loads(gr.text)
            content = base64.b64decode(doc['content']).decode()
            data = json.loads(content)
            # with open('data.json', 'w') as outfile:
            #    json.dump(data, outfile)
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
    except:
        logging.exception('Unexpected error:')
        raise


def SendResultsEmail(deleted_emails_count, errors_count):
    try:
        message = Mail(
            from_email='noreply@owasp.org',
            to_emails='ccapellan@gmail.com',
            subject='Daily Email Cleanup, ' + str(errors_count) + ' errors, ' + str(deleted_emails_count) + '  addresses disabled',
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
    except:
        logging.exception('Unexpected error sending email with results:')
        raise
