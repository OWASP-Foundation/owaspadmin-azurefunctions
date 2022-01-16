import logging

import os
import requests
import azure.functions as func
import urllib.parse
import json
import base64
import stripe

stripe.api_key = os.environ["STRIPE_SECRET"]

from datetime import datetime
from datetime import timedelta
from ..SharedCode.helperfuncs import MemberData
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.copper import OWASPCopper
from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError
mailchimp = MailChimp(mc_api=os.environ["MAILCHIMP_API_KEY"])

def main(req: func.HttpRequest) -> func.HttpResponse:
    post_data = req.get_body().decode("utf-8")
    post_dict = urllib.parse.parse_qs(post_data)

    token = post_dict.get('token')[0]

    if token != os.environ["SL_TOKEN_GENERAL"]:
        return func.HttpResponse(
            body='Invalid token',
            status_code=400
        )

    text = post_dict.get('text')[0]
    command = post_dict.get('command')[0]
    response_url = post_dict.get('response_url')[0]

    if command == '/contact-lookup':
        contact_lookup(text, response_url)

    if command == '/contact-details':
        contact_details(text, response_url)

    if command == '/stripe-details':
        stripe_details(text, response_url)

    return func.HttpResponse(
        body='',
        status_code=200
    )

def contact_lookup(text, response_url):

    member_data = None
    if '@' in text:
        member_data = MemberData.LoadMemberDataByEmail(text)
    else:
        member_data = MemberData.LoadMemberDataByName(text)

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
        fields.extend(
            {
                "type": "mrkdwn",
                "text": "*Membership Type*\n" + member_info.get('membership_type', None)
            },
            {
                "type": "mrkdwn",
                "text": "*Membership Start*\n" + member_info.get('membership_start', None)
            },
            {
                "type": "mrkdwn",
                "text": "*Membership End*\n" + member_info.get('membership_end', None)
            },
            {
                "type":"mrkdwn",
                "text":"*Company*\n" + member_info.get("company", None)
            })
        
        for leader_info in member_info['leader_info']:
            fields.append({
                "type":"mrkdwn",
                "text":f"*{leader_info['group-type']} Leader*\n{leader_info['group']}"
            })

        response_text['blocks'].append({
        "type": "section",
        "fields": fields
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

def contact_lookup_deprecated(text, response_url):
    returned_fields = 'email_address'

    search_results = mailchimp.search_members.get(
        query=urllib.parse.quote(text),
        list_id=os.environ["MAILCHIMP_LIST_ID"]
    )
    returned_members = search_results['full_search']['members']

    name_column = "*Name*\n"
    email_column = "*Email*\n"
    company_column = "*Company*\n"
    country_column = "*Country*\n"
    member_type_column = "*Membership Type*\n"
    member_start_column = "*Membership Start*\n"
    member_end_column = "*Membership End*\n"

    response_text = {
        "blocks": []
    }

    if len(returned_members) == 0:
        response_text['blocks'].append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "No results found for " + text
                }
            ]
        })

    for member in returned_members:
        
        membership_type = member['merge_fields']['MEMTYPE']

        response_text['blocks'].append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Name*\n" + member['merge_fields']['NAME']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Email*\n" + member['email_address']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Company*\n" + member['merge_fields']['COMPANY']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Country*\n" + member['merge_fields']['COUNTRY']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership Type*\n" + membership_type
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership Start*\n" + member['merge_fields']['MEMSTART']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership End*\n" + member['merge_fields']['MEMEND']
                }
            ]
        })

    send_response(response_text, response_url)


def contact_details(text, response_url):
    customers = stripe.Customer.list(
        email=text,
        limit=1
    )

    response_text = {
        "blocks": []
    }

    if len(customers) > 0:
        for customer in customers:
            if customer.email == text:
                customer_id = customer.id
                break
        charges = stripe.Charge.list(customer=customer_id)
        if len(charges) > 0:
            for charge in charges:
                amount = charge['amount'] / 100
                charge_date = datetime.fromtimestamp(charge['created']).strftime('%Y-%m-%d %H:%M:%S')
                response_text['blocks'].append({
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Transaction ID*\n" + charge['id']
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Date*\n" + charge_date
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Amount*\n" + str(amount) + '0'
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Card*\n" + charge['payment_method_details']['card']['brand'] + ' ending in ' + charge['payment_method_details']['card']['last4']
                        }
                    ]
                })
        else:
            response_text['blocks'].append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "No transactions found for " + text
                    }
                ]
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


def stripe_details(text, response_url):
    transaction = stripe.Charge.retrieve(text)
    amount = transaction['amount'] / 100
    charge_date = datetime.fromtimestamp(transaction['created']).strftime('%Y-%m-%d %H:%M:%S')

    response_text = {
        "blocks": [
            {
                "type": "section",
                "fields": []
            }
        ]
    }

    metadata = transaction.get('metadata', None)

    response_text['blocks'][0]['fields'].append({
        "type": "mrkdwn",
        "text": "*Transaction ID*\n" + transaction['id']
    })

    response_text['blocks'][0]['fields'].append({
        "type": "mrkdwn",
        "text": "*Date*\n" + charge_date
    })

    response_text['blocks'][0]['fields'].append({
        "type": "mrkdwn",
        "text": "*Amount*\n" + str(amount) + '0'
    })

    if metadata is None or metadata.get('purchase_type') == 'membership':
        response_text['blocks'][0]['fields'].append({
            "type": "mrkdwn",
            "text": "*Transaction Type*\nMembership Payment"
        })
    else:
        response_text['blocks'][0]['fields'].append({
            "type": "mrkdwn",
            "text": "*Transaction Type*\nDonation Payment"
        })

    response_text['blocks'][0]['fields'].append({
        "type": "mrkdwn",
        "text": "*Card*\n" + transaction['payment_method_details']['card']['brand'] + ' ending in ' + transaction['payment_method_details']['card']['last4']
    })

    if metadata is not None:
        response_text['blocks'][0]['fields'].append({
            "type": "mrkdwn",
            "text": "*Name*\n" + metadata.get('name', '')
        })

        response_text['blocks'][0]['fields'].append({
            "type": "mrkdwn",
            "text": "*Company*\n" + metadata.get('company', '')
        })

        response_text['blocks'][0]['fields'].append({
            "type": "mrkdwn",
            "text": "*Country*\n" + metadata.get('country', '')
        })

        response_text['blocks'][0]['fields'].append({
            "type": "mrkdwn",
            "text": "*Postal Code*\n" + metadata.get('postal_code', '')
        })

    return send_response(response_text, response_url)


def send_response(response_text, response_url):
    requests.post(response_url, json=response_text)


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