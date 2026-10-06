import logging
from urllib.parse import unquote_plus

from requests.packages import urllib3

from SharedCode import spotchk
import azure.functions as func
import json
import os
import re
import unicodedata
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From
from datetime import datetime
from ..SharedCode import recurringtoken
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.glueup import OWASPGlueup
from SharedCode import googleapi

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('provision email request.')  

    if not validate_call(req):
        return return_response('Call not valid (100)', False)

    # validation complete...let's do something...
    
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))    
    names = dict(x.split('=') for x in strbody.split('&'))
    
    gu = OWASPGlueup()
    customer = gu.getMemberByEmail(names.get('text'))

    if not customer:
        errors = {
            'email': ['No member found with this email address.  Unable to auto-provision email']
        }
        return return_response(errors, False)
    
    customer_name = customer.get('lastname', None) + ' ' + customer.get('firstname', None) if customer else None

    if customer_name is None or customer_name.strip() is None:
        errors = {
            'name': ['No first or last name.  Unable to auto-provision email']
        }
        return return_response(errors, False)
            
    # we need to test the personal email in Google Workspace to see if they already have an OWASP email address provisioned.  If they do, we cannot provision another one for them.
    og = OWASPGoogle()
    gUser = og.GetUser(request.get('text')) # lookup the user by personal email address
    primaryEmail = None
    if gUser:
        primaryEmail = gUser.get('primaryEmail', None)

    if primaryEmail:
        errors = {
            'email': ['Only one OWASP email address is allowed per member.']
        }
        return return_response(errors, False)
    else:
        primaryEmail = request.get('text')
    
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
        errors = {
            'email': ['Could not find a suitable alternate email.  Please submit a ticket at https://contact.owasp.org']
        }
        return return_response(errors, False)

    email = addresses[0] # use the first one in the list of possible email addresses which will be the preferred email address if it is available.  If not, it will be an alternate email address that is available.
    respb = True
    password = datetime.now().strftime('%m%d%Y') # generate a temporary password for the new user.  They will be required to change it upon first login.
    response = og.CreateSpecificEmailAddress(primaryEmail, first_name.capitalize(), last_name.capitalize(), email, password, True)
        
    if 'Failed' in response:
        respb = False
    else:
        # update the Glueup record with the new OWASP email address
        #customer['owaspemail'] = email
        #gu.updateMember(customer) # Yeah...thanks, Glueup, for nothing. Glueup's API does not allow updating a member record.  So, we will have to do this manually in Glueup.        
        sendProvisionEmailNotification(primaryEmail, password)
        response = f"Successfully provisioned email address: {email}."

    return return_response(response, respb)

def validate_call(req: func.HttpRequest) -> bool:
    body = req.get_body()
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return False
    names = dict(x.split('=') for x in strbody.split('&'))
    if not spotchk.spotchk().validate_query2(names):
        return False

    if not 'command' in names or not 'provision-email' in names['command']:
        return False
    
    return True

def return_response(response_str, success):
    if success:
        status_code = 200
        response = {
            "status": "OK",
            "data": response_str
        }
    else:
        status_code = 400
        response = {
            "status": "ERROR",
            "errors": response_str
        }
    headers = {"Content-Type":"application/json;charset=utf-8"}
                
    return func.HttpResponse(
        body=json.dumps(response),
        status_code=status_code,
        headers=headers
    )

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