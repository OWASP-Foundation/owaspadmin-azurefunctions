import logging
import os
import jwt
from jwt import algorithms
import azure.functions as func
import requests
import json
import base64
from ..SharedCode import helperfuncs
from ..SharedCode.googleapi import OWASPGoogle
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.copper import OWASPCopper
from ..SharedCode import recurringtoken
import stripe
from datetime import datetime
import re
import unicodedata

stripe.api_key = os.environ['STRIPE_SECRET']


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    #LogIpFromRequestHeaders(req)
    
    token = req.params.get('authtoken')
    if not token:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            token = req_body.get('authtoken')

    data = None
    if token:
        # do stuff here to decode the token and verify
        try:
            data = get_token_data(token)
        except Exception as err:
            logging.error(f'Invalid token: {err}')
        
        if not data:
            try:
                data = get_token_data_otp(token)
            except Exception as err:
                logging.error(f"Invalid token otp: {err}")
                
    acl = json.loads(os.environ['MP_ACL'])
    
    if data and len(data) >0: 
        member_info = get_member_info(data)

        return func.HttpResponse(json.dumps(member_info))
    else:
        return func.HttpResponse(
             "malformed request",
             status_code=404
        )

def get_public_keys():
    r = requests.get(os.environ['CF_TEAMS_DOMAIN'])
    public_keys = []
    jwk_set = r.json()
    for key_dict in jwk_set['keys']:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_dict))
        public_keys.append(public_key)
    return public_keys

def get_token_data(token):
    data = {}
    keys = get_public_keys()
    
    for key in keys:
        try:
            data = jwt.decode(token, key=key, algorithms=['RS256'], verify=True, options={"verify_aud": False})
            break
        except Exception as err:
            logging.info(f"Exception decoding token: {err}")
            pass

    return data

def get_token_data_otp(token):
    data = {}
    pub_key = jwt.algorithms.RSAAlgorithm.from_jwk(os.environ["CF_MEMBERSHIP_KEY_PUBLIC"])
    try:
        data = jwt.decode(token, pub_key, ['RS256'], options={"verify_aud": False, "verify": False})
    except Exception as err:
        logging.info(f"Exception decoding token OTP: {err}")
        pass

    return data

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

def get_member_info(data):
    logging.info(data)
    emailaddress = data['email']
    today = datetime.today()
    member_info = {}
    cp = OWASPCopper()
    opp = None
    person = None
    opptxt = cp.FindMemberOpportunity(emailaddress)
    if opptxt != None and 'Error:' not in opptxt:
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
        member_info = fill_leader_details(member_info)
        member_info = update_with_stripe_info(member_info, person)

    elif not opp:
        logging.info(f"Failed to get opportunity")
    else:
        logging.info(f"Failed to get person")
        
    logging.info(f"Member information: {member_info}")
    return member_info

def update_with_stripe_info(member_info, person):
    membership_email = None
    customer_id = None
    for email in person['emails']:
        customers = stripe.Customer.list(email=email['email'], api_key=os.environ['STRIPE_SECRET'])
        for customer in customers.auto_paging_iter():
            metadata = customer.get('metadata', None)
            if membership_email is None: # have not set email yet, get customer id
                customer_id = customer.get('id')

            if metadata and 'membership_type' in metadata:
                if metadata['membership_type'] == 'lifetime':
                    membership_email = email['email']
                    break
                elif 'membership_end' in metadata and helperfuncs.get_datetime_helper(metadata['membership_end']) > datetime.today():
                    membership_email = email['email']
                    break
                
    member_info['membership_email'] = membership_email
    if customer_id:
        member_info = get_stripe_billing_info(customer_id, member_info)

    return member_info

###################
### BELOW HERE IS BILLING MANAGEMENT STYLE - NEED TO UPDATE ABOVE WITH EXTRA INFO
###################

def get_stripe_billing_info(customer_id, member_info):
    customer = stripe.Customer.retrieve(
        customer_id,
        expand=['subscriptions', 'subscriptions.data.default_payment_method']
    )
    metadata = customer.get('metadata', {})
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
    if email != None and 'owasp.org' not in email.lower() and metadata.get('owasp_email', None) == None: 
        og = OWASPGoogle()
        customer_name = customer.get('name')
        if customer_name != None:
            first_name = customer_name.lower().strip().split(' ')[0]
            last_name = ''.join((customer_name.lower() + '').split(' ')[1:]).strip()
            nfn = unicodedata.normalize('NFD', first_name)
            nln = unicodedata.normalize('NFD', last_name)
            nfn = ''.join([c for c in nfn if not unicodedata.combining(c)])
            nln = ''.join([c for c in nln if not unicodedata.combining(c)])
            r2 = re.compile(r'[^a-zA-Z0-9]')
            first_name = r2.sub('',nfn)
            last_name = r2.sub('', nln)
            if first_name is not None:
                preferred_email = first_name 
                if last_name is not None and last_name != '':
                    preferred_email = preferred_email + '.' + last_name
                
                preferred_email = preferred_email + "@owasp.org"
                email_list = og.GetPossibleEmailAddresses(preferred_email)

    member_info['subscriptions'] = subscription_list
    member_info['emaillist'] = email_list
    member_info['customer_token'] = recurringtoken.make_token(customer.id).decode()
    return member_info
