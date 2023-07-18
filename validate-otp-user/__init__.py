import logging
import jwt
from jwt import algorithms
import os
import json
import requests
import azure.functions as func
from datetime import datetime, timedelta
from ..SharedCode.copper import OWASPCopper
from ..SharedCode import helperfuncs
import stripe
stripe.api_key = os.environ['STRIPE_SECRET']

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    token = {}
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        token = req_body.get('token')

    result = {
             "success": False,
             "iat": int(datetime.now().timestamp()),
             "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
             "nonce": ""
        }
    
    if token:
        logging.info(token)
        data = get_token_data(token)
        logging.info(data)

        if data:
            result["nonce"] = data["nonce"]
        
        if evaluateData(data):
            result["success"] = True
        
        # this needs to return a signed JWT
        #{ token: jwt }
        
        keystr = os.environ["CF_MEMBERSHIP_KEY_PRIVATE"]
        private_key = jwt.algorithms.RSAAlgorithm.from_jwk(keystr)
        jwtoken = None
        try:
            jwtoken = jwt.encode(result, key=private_key,algorithm='RS256')
            logging.info(jwtoken)
        except Exception as err:
            logging.info(f"Exception encoding token: {err}")

        
        try:
            logging.info(json.dumps({"token": jwtoken}))
        except Exception as err:
            logging.info(f"Exception dumping token: {err}")

        
        return func.HttpResponse(json.dumps({"token": jwtoken}), headers={ 'content-type': 'application/json' })
    else:
        return func.HttpResponse(
             json.dumps({"result":"false", "error":"failed to get token", "stack":"__init__.py main line 18"}),
             status_code=403,
             headers = {"content-type":"application/json"}
        )



def get_public_keys():
    r = requests.get(os.environ['CF_TEAMS_DOMAIN'])
    public_keys = {}
    jwk_set = r.json()
    for key_dict in jwk_set['keys']:
        kid = key_dict['kid']
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_dict))
        public_keys[kid] = public_key

    return public_keys

def get_token_data(token):
    data = {}
    keys = get_public_keys()
    kid = jwt.get_unverified_header(token)['kid']
    key = keys[kid]
    
    try:
        data = jwt.decode(token, key, ['RS256'], options={"verify_aud": False})
    except Exception as err:
        logging.info(f"Exception decoding token: {err}")
        pass

    return data

def evaluateData(data):    
    result = False
    email = data['identity']['email']
    logging.info("Attempting to validate " + email)
    member_info = get_member_info(email)
    if member_info:
        result = True
    else:
        logging.info("Found no membership for " + email)

    
    return result

def get_member_info(emailaddress):
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
        member_info['membership_email'] = get_membership_email(person)
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
        
    elif not opp:
        logging.info(f"Failed to get opportunity")
    else:
        logging.info(f"Failed to get person")
        
    logging.info(f"Member information: {member_info}")
    return member_info

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

def get_membership_email(person):
    membership_email = None
    for email in person['emails']:
        customers = stripe.Customer.list(email=email['email'], api_key=os.environ['STRIPE_SECRET'])
        for customer in customers.auto_paging_iter():
            metadata = customer.get('metadata', None)
            if metadata and 'membership_type' in metadata:
                if metadata['membership_type'] == 'lifetime':
                    membership_email = email['email']
                    break
                elif 'membership_end' in metadata and helperfuncs.get_datetime_helper(metadata['membership_end']) > datetime.today():
                    membership_email = email['email']
                    break
    
    return membership_email