import logging

import azure.functions as func

import os
import json
import pathlib
from typing import Dict

import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From

def main(req: func.HttpRequest) -> func.HttpResponse:
    request = req.get_json()
    errors = validate_request(request)

    if not bool(errors):
        checkout_type = request.get('checkout_type')

        if checkout_type == 'donation':
            response = start_donation_session(request)
        elif checkout_type == 'membership':
            response = start_membership_session(request)
        elif checkout_type == 'manage_membership':
            response = start_manage_membership_session(request)

        return return_response(response, True)
    else:
        return return_response(errors, False)


def validate_request(request: Dict) -> Dict:
    errors = {}
    checkout_type = request.get('checkout_type')

    if checkout_type and checkout_type in ['donation', 'membership']:
        if checkout_type == 'donation':
            if request.get('currency') is None or request.get('currency') not in ['usd', 'eur', 'gbp']:
                errors['currency'] = ['currency is required and must be usd, eur, or gbp']
            if request.get('amount') is None or request.get('amount') < 1:
                errors['amount'] = ['amount is required']
            if request.get('name') is None:
                errors['name'] = ['name is required']
            if request.get('email') is None:
                errors['email'] = ['email is required']
        if checkout_type == 'membership':
            if request.get('currency') is None or request.get('currency') not in ['usd', 'eur', 'gbp']:
                errors['currency'] = ['currency is required and must be usd, eur, or gbp']
            if request.get('name') is None:
                errors['name'] = ['name is required']
            if request.get('email') is None:
                errors['email'] = ['email is required']
            if request.get('membership_type') is None:
                errors['membership_type'] = ['membership type is required']
    elif checkout_type and checkout_type in ['manage_membership', 'manage_donation']:
        if request.get('email') is None:
            errors['email'] = ['email is required']
    else:
        errors['checkout_type'] = ['checkout_type is required and must be either donation, manage_membership, or manage_donation']

    return errors


def start_donation_session(request: Dict) -> Dict:
    api_request = make_donation_api_request(request)
    api_response = stripe.checkout.Session.create(**api_request)

    response = {
        "session_id": api_response['id']
    }

    return response


def start_membership_session(request: Dict) -> Dict:
    api_request = make_subscription_api_request(request)
    api_response = stripe.checkout.Session.create(**api_request)

    response = {
        "session_id": api_response['id']
    }

    return response


def start_manage_membership_session(request: Dict) -> Dict:
    member_email = request.get('email')

    customers = stripe.Customer.list(email=member_email)
    if len(customers) > 0:
        for customer in customers:
            if customer.email == member_email:
                subscriptions = stripe.Subscription.list(status='active', customer=customer.id)
                if len(subscriptions.data) > 0:
                    subscription_id = subscriptions.data[0].id
                    send_subscription_management_email(member_email, customer.id, subscription_id)
                break

    return {}


def send_subscription_management_email(member_email, customer_id, subscription_id):
    session = stripe.checkout.Session.create(
      payment_method_types=['card'],
      mode='setup',
      customer_email=member_email,
      setup_intent_data={
	'metadata': {
	  'customer_id': customer_id,
	  'subscription_id': subscription_id,
	},
      },
      success_url='https://www2.owasp.org/membership-update-success',
      cancel_url='https://www2.owasp.org/membership-update-cancel',
    )

    with open(pathlib.Path(__file__).parent / 'email-template.html') as dfile:
        email_contents = dfile.read()

    message_contents = 'Someone, hopefully you, just requested a link to update the payment information for your OWASP membership. In order to update your payment information, please click the link below. The link will be vaild for 24 hours, but you can request a new one at any time. Thanks for being a member of OWASP!'

    message_link = 'https://www2.owasp.org/manage-membership?token=' + session.id

    email_contents = email_contents.replace("{{ message_contents }}", message_contents)
    email_contents = email_contents.replace("{{ action_link }}", message_link)

    message = Mail(
        from_email=From('noreply@owasp.org', 'OWASP'),
        to_emails=member_email,
        subject='Manage Your OWASP Membership',
        html_content=email_contents)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        logging.info(str(e))


def make_donation_api_request(request: Dict) -> Dict:
    currency = request.get('currency')
    amount = request.get('amount') * 100
    recurring = request.get('recurring')
    mailing_list = request.get('mailing_list')
    repo_name = request.get('repo_name')
    project_title = request.get('project_title')
    attribution = request.get('attribution')
    email = request.get('email')
    name = request.get('name')
    source = request.get('source')

    if recurring is None:
        recurring = False
    if mailing_list is None:
        mailing_list = False
    if attribution is None:
        attribution = False

    api_request = {
        "success_url": "https://www2.owasp.org/donation-success",
        "cancel_url": "https://www2.owasp.org/donation-error",
        "payment_method_types": ["card"],
        "customer_email": email,
        "payment_intent_data": {
            "metadata": {
                "recurring": recurring,
                "mailing_list": mailing_list,
                "repo_name": repo_name,
                "project_title": project_title,
                "attribution": attribution,
                "name": name,
                "source": source,
                "purchase_type": "donation"
            }
        },
        "line_items": [
            {
                "name": "OWASP Donation",
                "amount": amount,
                "currency": currency,
                "quantity": 1
            }
        ]
    }

    return api_request


def make_subscription_api_request(request: Dict) -> Dict:
    currency = 'usd'
    country = request.get('country')['name']
    postal_code = request.get('postal_code')
    name = request.get('name')
    email = request.get('email')
    company = request.get('company')
    mailing_list = request.get('mailing_list')
    source = request.get('source')

    discount = request.get('discount')
    recurring = request.get('recurring')
    membership_type = request.get('membership_type')

    if recurring is None:
        recurring = False
    if mailing_list is None:
        mailing_list = False
    if company is None:
        company = ''
    if discount is None:
        discount = False

    metadata = {
        "recurring": recurring,
        "mailing_list": mailing_list,
        "discount": discount,
        "name": name,
        "company": company,
        "country": country,
        "postal_code": postal_code,
        "purchase_type": "membership"
    }

    api_request = {
        "success_url": "https://www2.owasp.org/membership-success",
        "cancel_url": "https://www2.owasp.org/membership-error",
        "payment_method_types": ["card"],
        "customer_email": email,
    }

    if recurring and membership_type == 'One Year':
        if discount:
            plan_id = 'plan_GFpBf2oPjNHdMs'
        else:
            plan_id = 'plan_GFpD49OD6Sbc0C'

        api_request['subscription_data'] = {
	    'items': [{
	      'plan': plan_id,
	    }],
            'metadata': metadata
        }

    else:
        if discount:
            amount = 2000
            description = 'OWASP Discounted One Year Membership'
        elif membership_type == 'One Year':
            amount = 5000
            description = 'OWASP One Year Membership'
        elif membership_type == 'Two Year':
            amount = 9500
            description = 'OWASP Two Year Membership'
        elif membership_type == 'Lifetime':
            amount = 50000
            description = 'OWASP Lifetime Membership'

        api_request['payment_intent_data'] = {
            "metadata": metadata        
        }

        api_request['line_items'] = [
            {
                "name": "OWASP Membership",
                "amount": amount,
                "description": description,
                "currency": 'usd',
                "quantity": 1
            }
        ]

    return api_request


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
