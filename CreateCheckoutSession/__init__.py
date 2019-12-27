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

from ..SharedCode import recurringtoken

import urllib.parse

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
            if request.get('amount') is None or int(request.get('amount')) < 1:
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
                customer_token = recurringtoken.make_token(customer.id)
                send_subscription_management_email(member_email, customer_token)
                break

    return {}


def send_subscription_management_email(member_email, customer_token):
    with open(pathlib.Path(__file__).parent / 'email-template.html') as dfile:
        email_contents = dfile.read()

    message_contents = 'Someone, hopefully you, just requested a link to update the billing information that OWASP uses for your membership of recurring donation. In order to update your payment information, please click the link below. The link will be vaild for 24 hours, but you can request a new one at any time. Thanks for supporting OWASP!'

    params = {'token': customer_token}
    
    message_link = 'https://www2.owasp.org/manage-membership?' + urllib.parse.urlencode(params)

    email_contents = email_contents.replace("{{ message_contents }}", message_contents)
    email_contents = email_contents.replace("{{ action_link }}", message_link)

    message = Mail(
        from_email=From('noreply@owasp.org', 'OWASP'),
        to_emails=member_email,
        subject='Manage Your OWASP Payment Information',
        html_content=email_contents)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        logging.info(str(e))


def make_donation_api_request(request: Dict) -> Dict:
    currency = request.get('currency')
    amount = int(request.get('amount')) * 100
    recurring = request.get('recurring')
    mailing_list = request.get('mailing_list')
    repo_name = request.get('repo_name')
    project_title = request.get('project_title')
    restricted = request.get('restricted')
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
    if restricted is None:
        restricted = False

    metadata = {
        "recurring": recurring,
        "mailing_list": mailing_list,
        "repo_name": repo_name,
        "project_title": project_title,
        "attribution": attribution,
        "restricted": restricted,
        "name": name,
        "source": source,
        "purchase_type": "donation"
    }

    api_request = {
        "success_url": "https://www2.owasp.org/donation-success",
        "cancel_url": "https://www2.owasp.org/donation-error",
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(email)
    if (stripe_customer_id is not None):
        api_request['customer'] = stripe_customer_id
    else:
        api_request['customer_email'] = email

    if recurring is True:
        plan_id = get_recurring_donation_plan_id(amount, currency)
        api_request['subscription_data'] = {
	    'items': [{
	      'plan': plan_id,
	    }],
            'metadata': metadata
        }

    else:
        api_request['payment_intent_data'] = {
            "metadata": metadata        
        }
        api_request['line_items'] = [
            {
                "name": "OWASP Donation",
                "amount": amount,
                "currency": currency,
                "quantity": 1
            }
        ]

    return api_request


def make_subscription_api_request(request: Dict) -> Dict:
    currency = 'usd'
    country = request.get('country')['name']
    postal_code = request.get('postal_code')
    name = request.get('name')
    email = request.get('email')
    company = request.get('company')
    student = request.get('student')
    university = request.get('university')
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
    if university is None:
        university = ''
    if student is None:
        student = False
    if discount is None:
        discount = False

    metadata = {
        "recurring": recurring,
        "mailing_list": mailing_list,
        "discount": discount,
        "name": name,
        "company": company,
        "university": university,
        "student": student,
        "country": country,
        "postal_code": postal_code,
        "purchase_type": "membership"
    }

    api_request = {
        "success_url": "https://www2.owasp.org/membership-success",
        "cancel_url": "https://www2.owasp.org/membership-error",
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(email)
    if (stripe_customer_id is not None):
        api_request['customer'] = stripe_customer_id
    else:
        api_request['customer_email'] = email

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
        if student:
            amount = 2000
            description = 'OWASP Student One Year Membershp'
        elif discount:
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


def get_recurring_donation_plan_id(amount, currency):
    plan_id = None
    plans = stripe.Plan.list(
        limit=100,
        product=os.environ["STRIPE_RECURRING_DONATION"]
    )
    for plan in plans.auto_paging_iter():
        if plan.get('active', False) and plan.get('amount') == amount and plan.get('currency') == currency:
            plan_id = plan.id
            break

    if plan_id is None:
        new_plan = stripe.Plan.create(
              amount=amount,
              currency=currency,
              interval="month",
              product=os.environ["STRIPE_RECURRING_DONATION"],
        )
        plan_id = new_plan.get('id')

    return plan_id


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


def get_stripe_customer_id(email):
    customers = stripe.Customer.list(email=email)
    if len(customers) > 0:
        for customer in customers:
            if customer.email == email:
                return customer.id

    return None
