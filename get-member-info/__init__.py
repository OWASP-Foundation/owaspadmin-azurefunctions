import logging
import os
import azure.functions as func
import requests
import json
import base64
from ..SharedCode import helperfuncs
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.copper import OWASPCopper
import stripe
from datetime import datetime

stripe.api_key = os.environ['STRIPE_SECRET']


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    LogIpFromRequestHeaders(req)
    
    email = req.params.get('email')
    if not email:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            email = req_body.get('email')

    if email and email=='harold.blankenship@owasp.com': #only work with this email address for now
        member_info = get_member_info(email)
        return func.HttpResponse(json.dumps(member_info))
    else:
        return func.HttpResponse(
             "malformed request",
             status_code=404
        )

def get_membership_type(opp):
    memtype = 'Unknown'
    if 'Complimentary' in opp['name']:
        memtype = 'complimentary'
    elif 'One' in opp['name']:
        memtype = 'one'
    elif 'Two' in opp['name']:
        memtype = 'two'
    elif 'Lifetime' in opp['name']:
        memtype = 'lifetime'

    return memtype

def get_membership_start(opp):
    start = helperfuncs.get_datetime_helper(opp['close_date'])
    retstr = 'YYYY-mm-dd'
    if start != None:
        retstr = start.strftime('%Y-%m-%d')
    
    return retstr

def get_membership_end(cp, opp):
    end = helperfuncs.get_datetime_helper(cp.GetCustomFieldValue(opp['custom_fields'], cp.cp_opportunity_end_date))
    endstr = ''
    if end != None:
        endstr = end.strftime('%Y-%m-%d')

    return endstr

def get_membership_recurring(cp, opp):
    retstr = 'no'
    if cp.GetCustomFieldValue(opp['custom_fields'], cp.cp_opportunity_autorenew_checkbox):
        retstr = 'yes'

    return retstr

def LogIpFromRequestHeaders(req):
    ipaddr = ''
    if 'X-Forwarded-For' in req.headers:
        ipaddrs = req.headers.get('X-Forwarded-For').split(',')
        for ipaddr in ipaddrs:
            logging.info(f"Ip Address forward: {ipaddr}")
        
    if 'X-Forwarded-Host' in req.headers:
        host = req.headers.get('X-Forwarded-Host')
        logging.info(f"Forward host is {host}")

    if ':authority:' in req.headers:
        logging.info(f"Authority: {req.headers.get(':authority:')}")


def get_member_info(emailaddress):
    today = datetime.today()
    member_info = {}
    cp = OWASPCopper()
    opp = None
    person = None
    opptxt = cp.FindMemberOpportunity(emailaddress)
    if opptxt != None:
        opp = json.loads(opptxt)
    pertext = cp.FindPersonByEmail(emailaddress)
    if pertext != '':
        people = json.loads(pertext)
        if len(people) > 0:
            person = people[0]

    if opp and person:
        member_info['membership_type'] = get_membership_type(opp)
        member_info['membership_start'] = get_membership_start(opp)
        member_info['membership_end'] = get_membership_end(cp, opp)
        member_info['membership_recurring'] = get_membership_recurring(cp, opp)
        member_info['name'] = person['name']
        member_info['emails'] = person['emails']
        member_info['address'] = person['address']
        member_info['phone_numbers'] = person['phone_numbers']
        member_info['member_number'] = cp.GetCustomFieldValue(person['custom_fields'], cp.cp_person_stripe_number)

    return member_info