import logging

import os
import requests
import azure.functions as func
import urllib.parse

import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]

from datetime import datetime
from datetime import timedelta

from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError
mailchimp = MailChimp(mc_api=os.environ["MAILCHIMP_API_KEY"])

def main(req: func.HttpRequest) -> func.HttpResponse:
    post_data = req.get_body().decode("utf-8")
    post_dict = urllib.parse.parse_qs(post_data)

    token = post_dict.get('token')[0]

    if token != os.environ["SL_TOKEN"]:
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

def contact_lookup2(text, response_url):
    customers = stripe.Customer.list(
        email=text,
        limit=1
    )

    customers.append(stripe.Customer.list(name=text))

    response_text = {
        "blocks": []
    }

    if len(customers) > 0:
        for customer in customers:
            response_text['blocks'].append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Name*\n" + customer.name
                },
                {
                    "type": "mrkdwn",
                    "text": "*Email*\n" + customer.email
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership Type*\n" + customer.metadata['membership_type']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership Start*\n" + customer.metadata['membership_start']
                },
                {
                    "type": "mrkdwn",
                    "text": "*Membership End*\n" + customer.metadata['membership_end']
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

def contact_lookup(text, response_url):
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
                    "text": "*Membership Type*\n" + member['merge_fields']['MEMTYPE']
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
