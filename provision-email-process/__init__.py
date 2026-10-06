import logging
import os
import unicodedata
import azure.functions as func
import requests
import json
import re
import secrets
import string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From
from datetime import datetime
from ..SharedCode import recurringtoken
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.glueup import OWASPGlueup

def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
       
    #load data from json string
    data = json.loads(msg.get_body().decode('utf-8'))
    if 'provision-email' in data['command']:
        email = data['text']
        result = provisionOWASPEmail(email)

        #notify slack that this was done...
        msgtext = f"Provision Email access for {email} result: {result}"
        response_url = data['response_url']
        headers = { 'Content-type':'application/json'}
        msgdata = {
            'text':msgtext,
            'response_type':'ephemeral'
        }
        requests.post(response_url, data=json.dumps(msgdata), headers = headers)
    else:
        logging.info(f"Request was not a provision-email command: {data}")


def provisionOWASPEmail(personal_email):
    gu = OWASPGlueup()
    customer = gu.getMemberByEmail(personal_email)

    if not customer:
        return f"No member found with email address {personal_email}.  Unable to auto-provision email."
    
    customer_name = customer.get('lastname', None) + ' ' + customer.get('firstname', None) if customer else None

    if customer_name is None or customer_name.strip() is None:
        return "No first or last name.  Unable to auto-provision email."
            
    # we need to test the personal email in Google Workspace to see if they already have an OWASP email address provisioned.  If they do, we cannot provision another one for them.
    og = OWASPGoogle()
    gUser = og.GetUser(personal_email) # lookup the user by personal email address
    primaryEmail = None
    if gUser:
        primaryEmail = gUser.get('primaryEmail', None)

    if primaryEmail:        
        return f"Failed to provision email address: {personal_email}.  Reason: Only one OWASP email address is allowed per member."
    else:
        primaryEmail = personal_email # use the personal email address as the secondary email address for the new OWASP email account.  This is required by Google Workspace to provision a new email account.
    
    first_name = customer_name.lower().strip().split(' ')[0]
    last_name = ''.join((customer_name.lower() + '').split(' ')[1:]).strip()
    nfn = unicodedata.normalize('NFD', first_name)
    nln = unicodedata.normalize('NFD', last_name)
    nfn = ''.join([c for c in nfn if not unicodedata.combining(c)])
    nln = ''.join([c for c in nln if not unicodedata.combining(c)])
    r2 = re.compile(r'[^a-zA-Z0-9]')
    first_name = r2.sub('',nfn)
    last_name = r2.sub('', nln)

    email = first_name + '.' + last_name + '@owasp.org'
    addresses = og.GetPossibleEmailAddresses(email)
    if len(addresses) == 0:
        return f"Failed to provision email address: {personal_email}.  Reason: Could not find a suitable alternate email."

    email = addresses[0] # use the first one in the list of possible email addresses which will be the preferred email address if it is available.  If not, it will be an alternate email address that is available.
    respb = True
    password = generate_strong_password() # generate a temporary password for the new user.  They will be required to change it upon first login.
    response = og.CreateSpecificEmailAddress(primaryEmail, first_name.capitalize(), last_name.capitalize(), email, password, True)
        
    if 'Failed' in response:
        response = f"Failed to provision email address: {email}.  Reason: {response}"
    else:
        # update the Glueup record with the new OWASP email address
        #customer['owaspemail'] = email
        #gu.updateMember(customer) # Yeah...thanks, Glueup, for nothing. Glueup's API does not allow updating a member record.  So, we will have to do this manually in Glueup.        
        sendProvisionEmailNotification(primaryEmail, password)
        response = f"Successfully provisioned email address: {email}."

    return response

def sendProvisionEmailNotification(email, password):
    hcontent = f"To access your owasp email account {email}, use <strong>{password}</strong><br>You will be required to change the password upon first login and please remember to set up 2fa.<br><br>Thank you,<br>OWASP Foundation"
        
    
    message = Mail(
    from_email=From('noreply@owasp.org', 'OWASP'),
    to_emails=email,
    html_content=hcontent, 
    subject="Your OWASP Email Account")
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        logging.warning(f"Failed to send mail to {email}.  Result: {str(e)}")

def generate_strong_password(length=16):
    if length < 12:
        raise ValueError("Password length should be at least 12 characters for security.")

    # Character pools
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*()-_=+[]{}<>?/"

    # Ensure minimum complexity
    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(symbols)
    ]

    # Fill the rest with a mix of all allowed characters
    all_chars = upper + lower + digits + symbols
    password += [secrets.choice(all_chars) for _ in range(length - len(password))]

    # Shuffle securely
    secrets.SystemRandom().shuffle(password)

    return "".join(password)