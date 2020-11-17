import logging

import azure.functions as func

import os
import json
import pathlib
from typing import Dict
from datetime import datetime
import urllib.parse

import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]

from ..SharedCode import recurringtoken
from ..SharedCode.googleapi import OWASPGoogle

def main(req: func.HttpRequest) -> func.HttpResponse:
    request = req.get_json()

    token = request.get('token', None)
    action = request.get('action', None)

    if token is None:
        errors = {
            'token': ['token is required']
        }
        return return_response(errors, False)

    customer_id = recurringtoken.decode_token(token)

    if action == 'info':
        return return_response(get_member_info(customer_id), True)

def IsExpired(metadata):
    expired = True
    #logging.info(f"Metadata: {metadata}")
    membership_type = metadata.get('membership_type', None)
    #logging.info(f"Membership Type: {membership_type}")
    if membership_type != None:
        membership_end = metadata.get('membership_end', None)
        if membership_type == 'lifetime':
            expired = False
        if expired:
            try:
                memend_date = datetime.strptime(membership_end, "%m/%d/%Y")
                if memend_date > datetime.now():
                    expired = False
            except:
                try:
                    memend_date = datetime.strptime(membership_end, "%Y-%m-%d")
                except:
                    pass
                memend_date = None
                #logging.warn('Expired membership')
                # no end date and not lifetime = no membership
    else:
        logging.warn('Metadata is empty or membership_type is None')
    return expired

def get_member_info(customer_id):
    customer = stripe.Customer.retrieve(
        customer_id,
        expand=['subscriptions', 'subscriptions.data.default_payment_method']
    )
    metadata = customer.get('metadata', {})

    membership_type = metadata.get('membership_type', None)

    membership_name = 'Unknown Membership Type'
    if membership_type is not None:
        if membership_type == 'one':
            membership_name = 'One Year Membership'
        elif membership_type == 'student':
            membership_name = 'One Year Student Membership'
        elif membership_type == 'two':
            membership_name = 'Two Year Membership'
        elif membership_type == 'lifetime':
            membership_name = 'Lifetime Membership'
        elif membership_type == 'honorary':
            membership_name = 'Honorary Membership'
        elif membership_type == 'complimentary':
            membership_name = 'Complimentary Membership'

        recurring = metadata.get('membership_recurring', 'no')

        if recurring == 'no':
            membership_recurring = False
        else:
            membership_recurring = True

        membership = {
            "membership_name": membership_name,
            "membership_recurring": membership_recurring,
            "membership_end": metadata.get('membership_end', None)
        }
    else:
        membership = {}

    subscription_list = []

    subscriptions = customer.get('subscriptions')
    for subscription in subscriptions:
        if subscription['status'] == 'active' and subscription['cancel_at_period_end'] is False:
            card_data = subscription['default_payment_method'].get('card', {})
            card_brand = card_data.get('brand', '').capitalize()
            card_exp_month = card_data.get('exp_month', '')
            card_exp_year = card_data.get('exp_year', '')
            card_last_4 = card_data.get('last4', '')

            if subscription['plan']['nickname'] is not None and  "Membership" in subscription['plan']['nickname']:
                subscription_type = "membership"
            else:
                subscription_type = "donation"

            next_billing_date = datetime.fromtimestamp(subscription['current_period_end']).strftime('%m/%d/%Y')
            subscription_name = subscription['plan']['nickname']

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='setup',
                customer_email=customer.email,
                setup_intent_data={
                    'metadata': {
                        'customer_id': customer.id,
                        'subscription_id': subscription.id
                    }
                },
                success_url='https://owasp.org/membership-update-success',
		cancel_url='https://owasp.org/membership-update-cancel',
            )

            subscription_list.append({
                "id": subscription.id,
                "checkout_session": session.id,
                "type": subscription_type,
                "next_billing_date": next_billing_date,
                "subscription_name": subscription_name,
                "card": {
                    "brand": card_brand,
                    "exp": str(card_exp_month) + '/' + str(card_exp_year),
                    "last_4": card_last_4
                }
            })
    email_list = []
    email = customer.get('email')
    if email != None and 'owasp.org' not in email.lower() and metadata.get('owasp_email', None) == None and not IsExpired(metadata): 
        og = OWASPGoogle()
        customer_name = customer.get('name')
        if customer_name != None:
            first_name = customer_name.lower().strip().split(' ')[0]
            last_name = ''.join((customer_name.lower() + '').split(' ')[1:]).strip()
            if first_name != None and last_name != None:
                preferred_email = first_name + '.' + last_name + '@owasp.org'    
                email_list = og.GetPossibleEmailAddresses(preferred_email)

    retdata = {
        "membership": membership,
        "subscriptions": subscription_list,
        "emaillist": email_list
    }

    return retdata


def return_response(response, success):
    if success:
        status_code = 200
        response = {
            "status": "OK",
            "data": response
        }
    else:
        status_code = 400
        response = {
            "status": "ERROR",
            "errors": response
        }

    return func.HttpResponse(
        body=json.dumps(response),
        status_code=status_code
    )
