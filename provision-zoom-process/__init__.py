from SharedCode.github import OWASPGitHub
import logging
import os
import azure.functions as func
import requests
import json
import base64
from ..SharedCode import helperfuncs
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.github import OWASPGitHub
import pathlib
import urllib


def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
   
    #load data from json string
    data = json.loads(msg.get_body().decode('utf-8'))
    if 'provision-zoom' in data['command']:
        group_url = data['text']
        create_zoom_account(group_url)

        #notify slack that this was done...
        msgtext = f"Successfully provisioned Zoom access for {group_url}"
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

def create_zoom_account(chapter_url):
    #creating a zoom account requires
    #  1.) creating a [chapter-name]-leaders@owasp.org group account
    #  2.) adding leaders to group
    #  3.) determining which zoom group to put them in (currently 4 groups)

    #  4.) sending onetimesecret link with password to person who requested access
    chapter_name = chapter_url.replace('www-projectchapter-','').replace('www-chapter-', '').replace('www-project-', '').replace('www-committee-','').replace(' ', '-')
    leadersemail = f"{chapter_name}-leaders@owasp.org"

    logging.info(f"Provisioning Zoom for {chapter_url}")
    leaders = []
    gh = OWASPGitHub()
    leaders = gh.GetLeadersForRepo(chapter_url)

    if len(leaders) > 0:
        og = OWASPGoogle()
        result = og.FindGroup(leadersemail)
        leader_emails = []
        if result == None:
            result = og.CreateGroup(chapter_name, leadersemail)
        if not 'Failed' in result:    
            for leader in leaders:
                leader_emails.append(leader['email'])
                og.AddMemberToGroup(leadersemail, leader['email'])
        else:
            logging.error(f"Failed to find or create group for {leadersemail}.  Reason:{result}")

        if not 'Failed' in result:
            # if an account is added to SHARED_ZOOM_ACCOUNTS, remember to also add the associated password in the appropriate credential
            # further, if passwords change on the accounts they MUST be changed in Configuration as well
            zoom_accounts = json.loads(os.environ['SHARED_ZOOM_ACCOUNTS'])
            sorted_accounts = retrieve_member_counts(zoom_accounts)
            # the list is sorted by count so first one is golden..
            use_group = sorted_accounts[0]['account']
            result = og.FindGroup(use_group)
            if result != None and not 'Failed' in result:
                logging.info(f"Adding {leadersemail} to {use_group}")
                og.AddMemberToGroup(use_group, leadersemail, 'MEMBER', 'GROUP')
            else:
                logging.error(f"Failed to find group for {use_group}")

            zoom_account = use_group[0:use_group.find('@')]
            
            logging.info("Sending one time secret to leaders' emails.")
            helperfuncs.send_onetime_secret(leader_emails, os.environ[zoom_account.replace('-', '_') +'_pass'])
    else:
        logging.error(f"No leaders found for {chapter_url}")

    return None