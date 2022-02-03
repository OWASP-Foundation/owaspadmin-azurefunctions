import os
import requests
import azure.functions as func
import json
import base64
import stripe
import logging

from datetime import timedelta, datetime
from ..SharedCode.helperfuncs import MemberData
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.copper import OWASPCopper

stripe.api_key = os.environ["STRIPE_SECRET"]

def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    
    post_dict = json.loads(msg.get_body().decode("utf-8"))

    text = post_dict.get('text')
    command = post_dict.get('command')
    response_url = post_dict.get('response_url')

    if command == '/contact-lookup':
        contact_lookup(text, response_url)
    else:
        logging.error("Unknown command. Received: %s", command)


def contact_lookup(text, response_url):
    logging.info("Looking up %s", text)
    copper = OWASPCopper()
    member_data = None
    if '@' in text:
        member_data = MemberData.LoadMemberDataByEmail(text)
    else:
        persons = copper.FindPersonByNameObj(text)
        if len(persons) == 1:
            member_data = MemberData.LoadMemberDataByName(text)
        elif len(persons) > 1:
            contact_lookup_multiple(persons, response_url)
            return
            

    response_text = {
        "blocks": []
    }

    if member_data:        
        member_info = get_member_info(member_data)
        
        fields = []
        fields.append({
                "type": "mrkdwn",
                "text": "*Name*\n" + member_info.get('name', 'Unknown')
            })
        email_list = ", ".join([str(x['email']) for x in member_info.get('emails')])
        fields.append({
            "type":"mrkdwn",
            "text": "*Emails*\n" + email_list
        })
        address = member_info.get('address')
        if address:
            addressstr = f"{address.get('street')}\n{address.get('city')}, {address.get('state')} {address.get('postal_code')}, {address.get('country')}"

        fields.append({
            "type":"mrkdwn",
            "text":"*Address*\n" + addressstr
        })
        phone_list = ", ".join([str(x['number']) for x in member_info.get('phone_numbers')])
        fields.append({
            "type":"mrkdwn",
            "text": "*Phone Numbers*\n" + phone_list
        })
        memend = member_info.get('membership_end', None)
        if not memend:
            memend = 'None'
        memtype = member_info.get('membership_type', None)
        if not memtype:
            memtype = 'None'
        memstart = member_info.get('membership_start', None)
        if not memstart:
            memstart = 'None'
        company = member_info.get('company', None)
        if not company:
            company = 'None'
        
        response_text['blocks'].append({
            "type": "section",
            "text": {
                "text":"## Contact Information",
                "type":"mrkdwn"
                },
            "fields": fields
            }) 

        member_fields = []        
        member_fields.extend([
            {
                "type": "mrkdwn",
                "text": "*Membership Type*\n" + memtype
            },
            {
                "type": "mrkdwn",
                "text": "*Membership Start*\n" + memstart
            },
            {
                "type": "mrkdwn",
                "text": "*Membership End*\n" + memend
            },
            {
                "type":"mrkdwn",
                "text":"*Company*\n" + company
            }])
        
        response_text['blocks'].append({
        "type": "section",
        "text": {
            "text":"## Member Information",
            "type":"mrkdwn"
            },
        "fields": member_fields
        })

        leader_fields = []
        for leader_info in member_info['leader_info']:
            leader_fields.append({
                "type":"mrkdwn",
                "text":f"*{leader_info['group-type'].capitalize()} Leader*\n{leader_info['group']}"
            })

        if len(leader_fields) > 0:
            response_text['blocks'].append({
                "type":"section",
                "text": {
                    "text":"## Leadership Information",
                    "type":"mrkdwn"
                },
                "fields": leader_fields
            })
            
    else:
        response_text['blocks'].append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "No customer records found for " + text
                }
            ]
        })


    return send_response(response_text, response_url)


def contact_lookup_multiple(persons, response_url):

    response_text = {
        "blocks": []
    }

    for person in persons:
        member_data = MemberData.LoadMemberDataByEmail(person['emails'][0]['email'])
        if member_data:        
            member_info = get_member_info(member_data)
            
            fields = []
            fields.append({
                    "type": "mrkdwn",
                    "text": "*Name*\n" + member_info.get('name', 'Unknown')
                })
            email_list = ", ".join([str(x['email']) for x in member_info.get('emails')])
            fields.append({
                "type":"mrkdwn",
                "text": "*Emails*\n" + email_list
            })
            address = member_info.get('address')
            if address:
                addressstr = f"{address.get('street')}\n{address.get('city')}, {address.get('state')} {address.get('postal_code')}, {address.get('country')}"

            fields.append({
                "type":"mrkdwn",
                "text":"*Address*\n" + addressstr
            })
            phone_list = ", ".join([str(x['number']) for x in member_info.get('phone_numbers')])
            fields.append({
                "type":"mrkdwn",
                "text": "*Phone Numbers*\n" + phone_list
            })
            memend = member_info.get('membership_end', None)
            if not memend:
                memend = 'None'
            memtype = member_info.get('membership_type', None)
            if not memtype:
                memtype = 'None'
            memstart = member_info.get('membership_start', None)
            if not memstart:
                memstart = 'None'
            company = member_info.get('company', None)
            if not company:
                company = 'None'
            
            fields.extend([
                {
                    "type": "mrkdwn",
                    "text": "*Membership Type*\n" + memtype
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership Start*\n" + memstart
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership End*\n" + memend
                },
                {
                    "type":"mrkdwn",
                    "text":"*Company*\n" + company
                }])
            
            for leader_info in member_info['leader_info']:
                fields.append({
                    "type":"mrkdwn",
                    "text":f"*{leader_info['group-type']} Leader*\n{leader_info['group']}"
                })

            response_text['blocks'].append({
            "type": "section",
            "fields": fields
            })

    if len(response_text['blocks']) == 0:
        response_text['blocks'].append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "No customer records found."
                }
            ]
        })

    return send_response(response_text, response_url)

def fill_leader_details(memberinfo):
    gh = OWASPGitHub()
    r = gh.GetFile('owasp.github.io', '_data/leaders.json')
    leader_infos = []
    if r.ok:
        doc = json.loads(r.text)
        content = base64.b64decode(doc['content']).decode(encoding='utf-8')
        leaders = json.loads(content)
        for email in memberinfo['emails']:
            for sub in leaders:
                if sub['email'] and sub['email'].lower() == email['email'].lower():
                    leader_infos.append(sub)
            
        memberinfo['leader_info'] = leader_infos

    return memberinfo

def get_member_info(member_data):
    emailaddress = member_data.email
    member_info = {}
    cp = OWASPCopper()
    person = None
    person = cp.FindPersonByEmailObj(emailaddress)

    if person and len(person) > 0:
        person = person[0]
        member_info['membership_type'] = member_data.type
        memstart = None
        if member_data.start != None:
            memstart = datetime.strftime(member_data.start, "%Y-%m-%d")
        member_info['membership_start'] = memstart
        memend = None
        if member_data.end != None:
            memend = datetime.strftime(member_data.end, "%Y-%m-%d")
        member_info['membership_end'] = memend
        member_info['membership_recurring'] = member_data.recurring
        member_info['name'] = member_data.name
        member_info['emails'] = person['emails']
        if 'address' not in person or not person['address']:
            person['address'] = "{'street':'','city':'','state':'','postal_code':'','country':''}"
        else:
            if not person['address']['street']:
                person['address']['street'] = ''
            if not person['address']['city']:
                person['address']['city'] = ''
            if not person['address']['state']:
                person['address']['state']=''
            if not person['address']['postal_code']:
                person['address']['postal_code']=''
            if not person['address']['country']:
                person['address']['country']=''
        member_info['address'] = person['address']
        member_info['phone_numbers'] = person['phone_numbers']
        member_info['member_number'] = cp.GetCustomFieldValue(person['custom_fields'], cp.cp_person_stripe_number)
        member_info['company'] = person['company_name']
        member_info = fill_leader_details(member_info)
    else:
        logging.info(f"Failed to get person")
        
    return member_info

def send_response(response_text, response_url):
    logging.info("Sending response %s", response_text)
    response = requests.post(response_url, json=response_text)
    if not response.ok:
        logging.error(response)