import logging
import os
import azure.functions as func
import requests
import json
import base64
from ..SharedCode import helperfuncs
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.owasp_web import OWASPWeb
import pathlib
import urllib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From

# Updated 28_SEPT_2026
# This function is triggered by a message in the Azure Queue.
# Now uses new website and takes the chapter name instead of the repo
def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
   
    #load data from json string
    data = json.loads(msg.get_body().decode('utf-8'))
    if 'provision-zoom' in data['command']:
        group_name = data['text']
        result = create_zoom_account(group_name)

        #notify slack that this was done...
        msgtext = f"Provision Zoom access for {group_url} result: {result}"
        response_url = data['response_url']
        headers = { 'Content-type':'application/json'}
        msgdata = {
            'text':msgtext,
            'response_type':'ephemeral'
        }
        requests.post(response_url, data=json.dumps(msgdata), headers = headers)
    else:
        logging.info(f"Request was not a provision-zoom command: {data}")

def retrieve_member_counts(zoom_accounts):
    counts = []
    og = OWASPGoogle()
    for za in zoom_accounts:
        data = {'account': za, 'count': 0 }
        members = og.GetGroupMembers(za)
        data['count'] = len(members['members'])
        counts.append(data)

    return sorted(counts, key=lambda group: group['count'])

def send_zoominfo_email(member_email, zoom_email):
    hcontent = f"You have been assigned to <strong>{zoom_email}&#64;owasp.org</strong><br>You should receive a separate email with the password for this account. Because this is a shared account, please coordinate with other members on the account, do not change account details, and do not change the account password.<br><br>Thank you,<br>OWASP Foundation"
    message = Mail(
	from_email=From('noreply@owasp.org', 'OWASP'),
	to_emails=member_email,
	html_content=hcontent, 
    subject="Your Zoom Account")
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        logging.warn(f"Failed to send mail to {member_email}.  Result: {str(e)}")

def send_zoompw_email(leader_emails, zoom_pw):
    hcontent = f"To access your shared zoom account, use <strong>{zoom_pw}</strong><br>You should receive a separate email with the account login for this account. Because this is a shared account, please coordinate with other members on the account, do not change account details, and do not change the account username.<br><br>Thank you,<br>OWASP Foundation"
        
    
    message = Mail(
    from_email=From('noreply@owasp.org', 'OWASP'),
    to_emails=leader_emails,
    html_content=hcontent, 
    subject="Your Zoom Account")
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        logging.warn(f"Failed to send mail to {leader_emails}.  Result: {str(e)}")

def IsAlreadyProvisioned(groupemail, zoomaccounts):
    og = OWASPGoogle()
    for account in zoomaccounts:
        members = og.GetGroupMembers(account)
        for member in members['members']:
            if groupemail.lower() == member['email'].lower():
                return account
    
    return None

def create_zoom_account(group_name):
    #creating a zoom account requires
    #  1.) creating a [chapter-name]-leaders@owasp.org group account
    #  2.) adding leaders to group
    #  3.) determining which zoom group to put them in (currently 4 groups)

    #  4.) sending onetimesecret link with password to person who requested access
    chapter_name = group_name.replace('www-projectchapter-','').replace('www-chapter-', '').replace('www-project-', '').replace('www-committee-','').replace('www-revent', '').replace('OWASP', '').replace(' ', '-').lower()
    leadersemail = f"{chapter_name}-"
    if 'www-committee-' in chapter_name:
        leadersemail += "committee-"
    leadersemail += "leaders@owasp.org"
    
    zoom_accounts = json.loads(os.environ['SHARED_ZOOM_ACCOUNTS'])
    provision_account = IsAlreadyProvisioned(leadersemail, zoom_accounts)
    if provision_account:
        logging.info(f"Account {provision_account} already provisioned for {group_name}")
        return f"Account {provision_account} Already Provisioned"

    logging.info(f"Provisioning Zoom for {group_name}")
    leaders = []    
    ow = OWASPWeb()
    details = ow.getChapterDetails(group_name)
    if details and 'chapter' in details:
        leaders = ow.getLeaders(details['chapter']['id'])        

    leader_emails = []
    og = OWASPGoogle()
    result = og.FindGroup(leadersemail)
    if result == None:
        result = og.CreateGroup(chapter_name, leadersemail)
    if 'Failed' in result:
        logging.error(f"Failed to find or create group for {leadersemail}.  Reason:{result}")
        #return f"Could not create or find group for {leadersemail}"

    for leader in leaders:
        leader_emails.append(leader['contact'])
        if not 'Failed' in result: # add leader to group if it exists   
            og.AddMemberToGroup(leadersemail, leader['contact'])
    
    if len(leaders) > 0 and len(leader_emails) > 0:
        
        if not 'Failed' in result:
            # if an account is added to SHARED_ZOOM_ACCOUNTS, remember to also add the associated password in the appropriate credential
            # further, if passwords change on the accounts they MUST be changed in Configuration as well
            
            sorted_accounts = retrieve_member_counts(zoom_accounts)
            # the list is sorted by count so first one is golden..
            use_group = sorted_accounts[0]['account']
            result = og.FindGroup(use_group)
            if result != None and not 'Failed' in result:
                logging.info(f"Adding {leadersemail} to {use_group}")
                og.AddMemberToGroup(use_group, leadersemail, 'MEMBER', 'GROUP')
            else:
                logging.error(f"Failed to find group for {use_group}")
                return f"No group found for {use_group}"

            zoom_account = use_group[0:use_group.find('@')]
            
            # should send email to leaders group indicating which zoom group they are in...
            send_zoominfo_email(leadersemail, zoom_account)

            # send email to each leader indicating group password
            send_zoompw_email(leader_emails, os.environ[zoom_account.replace('-', '_') + '_pass'])          
    else:
        logging.error(f"No leaders found for {group_name}")
        return f"No Leaders in {group_name}"

    return "Account Provisioned"