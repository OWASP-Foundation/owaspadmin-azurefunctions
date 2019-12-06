import logging

import azure.functions as func

import os
import json
import hashlib
from datetime import datetime
from datetime import timedelta
from typing import Dict

import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]

from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError
mailchimp = MailChimp(mc_api=os.environ["MAILCHIMP_API_KEY"])

def main(req: func.HttpRequest) -> func.HttpResponse:
    payload = req.get_json()
    event = None

    try:
        event = stripe.Event.construct_from(
            payload, os.environ["STRIPE_SECRET"]
        )
    except ValueError as e:
        return func.HttpResponse(status_code=400)

    if event.type == 'checkout.session.completed':
        event_data = event.data.object
        handle_checkout_session_completed(event_data)

    return func.HttpResponse(status_code=200)


def handle_checkout_session_completed(event: Dict):
    payment_intent = event.get('payment_intent', None)
    subscription = event.get('subscription', None)
    customer_id = event.get('customer', None)
    customer_email = event.get('customer_email', None)
    subscription_data = {}

    if payment_intent is not None:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent)
        metadata = payment_intent.get('metadata', {})
        purchase_type = metadata.get('purchase_type', 'donation')
        
        if purchase_type == 'membership':
            subscription_data = get_subscription_data_from_event(event)

    if subscription is not None:
        subscription = stripe.Subscription.retrieve(subscription)
        metadata = subscription.get('metadata', {})
        subscription_data = get_subscription_data(payment_intent, subscription)

    add_to_mailing_list(customer_email, metadata, subscription_data)


def get_subscription_data_from_event(event):
    description = event["display_items"][0]["custom"]["description"]

    if "One Year" in description:
        membership_type = 'one'
        period_end = datetime.now() + timedelta(days=365)
        period_end = period_end.strftime('%m/%d/%Y')
    if "Two Year" in description:
        membership_type = 'two'
        period_end = datetime.now() + timedelta(days=730)
        period_end = period_end.strftime('%m/%d/%Y')
    if "Lifetime" in description:
        membership_type = 'lifetime'
        period_end = None

    return {
        "membership_end": period_end,
        "membership_type": membership_type
    }


def get_subscription_data(subscription):
    period_end = datetime.utcfromtimestamp(subscription["current_period_end"]).strftime('%m/%d/%Y')
    memership_type = 'one'

    return {
        "membership_end": period_end,
        "membership_type": membership_type
    }


def add_to_mailing_list(email, metadata, subscription_data):
    subscriber_hash = get_mailchimp_subscriber_hash(email)

    request_data = {
        "email_address": email,
        "status_if_new": "subscribed",
        "status": "subscribed",
        "merge_fields": get_merge_fields(metadata, subscription_data),
        "interests": get_interests(metadata),
        "marketing_permissions": get_marketing_permissions(metadata)
    }

    list_member = mailchimp.lists.members.create_or_update(os.environ["MAILCHIMP_LIST_ID"], subscriber_hash, request_data)

    return list_member


def get_marketing_permissions(metadata):
    if metadata.get('mailing_list', 'False') == 'True':
        return [
            {
                "marketing_permission_id": os.environ["MAILCHIMP_MKTG_PERMISSIONS_ID"],
                "enabled": True
            }
        ]
    else:
        return [
            {
                "marketing_permission_id": os.environ["MAILCHIMP_MKTG_PERMISSIONS_ID"],
                "enabled": False
            }
        ]


def get_interests(metadata):
    purchase_type = metadata.get('purchase_type')

    if purchase_type == 'donation':
        return {
            os.environ["MAILCHIMP_DONOR_GROUP_ID"]: True
        }
    else:
        return {
            os.environ["MAILCHIMP_MEMBER_GROUP_ID"]: True
        }


def get_merge_fields(metadata, subscription_data):
    merge_fields = {}

    purchase_type = metadata.get('purchase_type', 'donation')
    name = metadata.get('name')
    source = metadata.get('source')

    merge_fields['NAME'] = name

    if source is not None:
        merge_fields['SOURCE'] = source

    if purchase_type == 'membership':
        company = metadata.get('company')
        country = metadata.get('country')
        postal_code = metadata.get('postal_code')

        merge_fields['MEMSTART'] = datetime.today().strftime('%m/%d/%Y')

        membership_end = subscription_data.get('membership_end', None)
        membership_type = subscription_data.get('membership_type', None)

        if membership_end is not None:
            merge_fields['MEMEND'] = membership_end
        if membership_type is not None:
            merge_fields['MEMTYPE'] = membership_type
        if company is not None:
            merge_fields['COMPANY'] = company
        if country is not None:
            merge_fields['COUNTRY'] = country
        if postal_code is not None:
            merge_fields['POSTALCODE'] = postal_code

    return merge_fields


def get_mailchimp_subscriber_hash(email):
    email = email.lower()
    hashed = hashlib.md5(email.encode('utf8'))

    return hashed.hexdigest()
