import logging

import azure.functions as func
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity

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
from datetime import datetime, timedelta
import urllib.parse

def main(req: func.HttpRequest) -> func.HttpResponse:
    # seems to be the external public ip address
    ip_entry = {
        'PartitionKey':'billingipentries',
        'RowKey': GetIpFromRequestHeaders(req),
        'count': -1,
        'time': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    request = req.get_json()
    errors = validate_request(request)
    response = ''
    if not bool(errors):
        checkout_type = request.get('checkout_type')

        if checkout_type == 'donation':
            #this is the only place we currently need the ip restrictions...
            if throttle_ip_requests(ip_entry):
               logging.warn('this request was throttled based on ip')
               return return_response({'amount':['Invalid Request']}, False) 
            response = start_donation_session(request)
        elif checkout_type == 'membership':
            response = start_membership_session(request)
        elif checkout_type == 'manage_membership':
            response = start_manage_membership_session(request)

        return return_response(response, True)
    else:
        return return_response(errors, False)

def throttle_ip_requests(ip_entry):
    max_from_single_ip = 5
    table_service = TableService(account_name=os.environ['STORAGE_ACCOUNT'], account_key=os.environ['STORAGE_KEY'])
    table_service.create_table(table_name=os.environ['BILLING_TABLE']) #create if it doesn't exist
    ip_row = None
    try:
        ip_row = table_service.get_entity(os.environ['BILLING_TABLE'], ip_entry['PartitionKey'], ip_entry['RowKey'])
    except:
        pass
    if not ip_row:
        ip_entry['count'] = 1
        table_service.insert_entity(table_name=os.environ['BILLING_TABLE'], entity=ip_entry)
        ip_row = ip_entry
    else:
        lastdatetime = datetime.strptime(ip_row['time'], "%d/%m/%Y %H:%M:%S")
        currdatetime = datetime.strptime(ip_entry['time'], "%d/%m/%Y %H:%M:%S")
        tdelta = currdatetime - lastdatetime
        if tdelta.days < 1 and ip_row['count'] > max_from_single_ip:
            return True # throttle this entry..
        elif tdelta.days > 0: #over 1 day has passed, update the count to 1 and reset time
            ip_row['count'] = 1
            ip_row['time'] = currdatetime.strftime("%d/%m/%Y %H:%M:%S")
            table_service.update_entity(os.environ['BILLING_TABLE'], ip_row)
        else: # less than 1 day but count is < max_from_single_ip, update the count
            ip_row['count'] = ip_row['count'] + 1
            table_service.update_entity(os.environ['BILLING_TABLE'], ip_row)

    # However we got here, do not throttle
    return False


def GetIpFromRequestHeaders(req):
    ipaddr = ''
    if 'X-Forwarded-For' in req.headers:
        ipaddrs = req.headers.get('X-Forwarded-For').split(',')
        if len(ipaddrs) > 0:
            ipaddr = ipaddrs[0][:ipaddrs[0].find(':')]

    return ipaddr

def validate_request(request: Dict) -> Dict:
    errors = {}
    checkout_type = request.get('checkout_type')

    if checkout_type and checkout_type in ['donation', 'membership']:
        if checkout_type == 'donation':
            if request.get('currency') is None or request.get('currency') not in ['usd', 'eur', 'gbp']:
                errors['currency'] = ['currency is required and must be usd, eur, or gbp']
            if request.get('amount') is None or int(request.get('amount')) < 10:
                errors['amount'] = ['amount >= 10 is required']
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
    testmode = (member_email == "thewarfarin@hotmail.com")
    if testmode:
        customer_token = recurringtoken.make_token("twhm_39282991")
        send_subscription_management_email(member_email, customer_token)
        return

    customers = stripe.Customer.list(email=member_email)
    if len(customers) > 0:
        for customer in customers:
            metadata = customer.get('metadata', None)
            memtype = None
            if metadata:
                memtype = metadata.get('membership_type', None)

            if metadata and memtype: #could have 2 or more with same email, we want the membership one
                customer_token = recurringtoken.make_token(customer.id)
                send_subscription_management_email(member_email, customer_token)
                break
        
    return {}


def send_subscription_management_email(member_email, customer_token):
    params = {'token': customer_token}
    message_link = 'https://owasp.org/manage-membership?' + urllib.parse.urlencode(params)

    message = Mail(
	from_email=From('noreply@owasp.org', 'OWASP'),
	to_emails=member_email,
	html_content='<strong>Manage Billing</strong>')
    message.dynamic_template_data = {
	'manage_link': message_link
    }
    message.template_id = 'd-8d6003cb7bae478492ec9626b9e31199'
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
    email = request.get('email').lower()
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
        "success_url": "https://owasp.org/donation-success",
        "cancel_url": "https://owasp.org/donation-error",
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(email, name)
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
    email = request.get('email').lower()
    company = request.get('company')
    student = request.get('student')
    university = request.get('university')
    mailing_list = request.get('mailing_list')
    source = request.get('source')

    address = request.get('address')
    address2 = request.get('address2')
    city = request.get('city')
    state = request.get('state')

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
    if address is None:
        address = ''
    if address2 is None:
        address2 = ''
    if city is None:
        city = ''
    if state is None:
        state = ''

    metadata = {
        "recurring": recurring,
        "mailing_list": mailing_list,
        "discount": discount,
        "name": name,
        "company": company,
        "university": university,
        "student": student,
        "country": country,
        "address": address,
        "address2": address2,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "purchase_type": "membership"
    }

    api_request = {
        "success_url": "https://owasp.org/membership-success",
        "cancel_url": "https://owasp.org/membership-error",
        "payment_method_types": ["card"],
    }

    stripe_customer_id = get_stripe_customer_id(email, name, address, address2, city, state, postal_code, country)
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
        if discount and student:
            amount = 800
            description = 'OWASP Discounted Student One Year Membership'
        elif student:
            amount = 2000
            description = 'OWASP Student One Year Membershp'
        elif discount and membership_type == 'One Year':
            amount = 2000
            description = 'OWASP Discounted One Year Membership'
        elif membership_type == 'One Year':
            amount = 5000
            description = 'OWASP One Year Membership'
        elif discount and membership_type == 'Two Year':
            amount = 3500 
            description = 'OWASP Discounted Two Year Membership'
        elif membership_type == 'Two Year':
            amount = 9500 
            description = 'OWASP Two Year Membership'
        elif discount and membership_type == 'Lifetime':
            amount = 20000
            description = 'OWASP Discounted Lifetime Membership'
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


def get_stripe_customer_id(email, name='', address='', address2='', city='', state='', postal_code='', country=''):
    customers = stripe.Customer.list(email=email)
    if len(customers) > 0:
        for customer in customers:
            if customer.email == email:
                stripe.Customer.modify(
                                    customer.id,
                                    address={"line1":address, "line2":address2, "city":city, "state":state, "postal_code":postal_code, "country":country},
                                    )
                return customer.id
    else: # create the customer first
        customer_request = stripe.Customer.create(email=email.lower(),
                                                  name=name,
                                                  api_key=os.environ["STRIPE_SECRET"],
                                                  address = {"line1":address, "line2":address2, "city":city, "state":state, "postal_code":postal_code, "country":country}
                                                )
        
        return customer_request['id']

    return None
