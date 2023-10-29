import logging
import json
import re
import azure.functions as func
from ..SharedCode.github import OWASPGitHub
from ..SharedCode import helperfuncs
from ..SharedCode.copper import OWASPCopper

import base64
from datetime import datetime, timedelta
import stripe

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    email = req.params.get('email')
    name = req.params.get('name')
    membership_type = req.params.get('membership_type')
    country = req.params.get('country')
    postal_code = req.params.get('postal_code')
    company = req.params.get('company')
    university = req.params.get('university')
    mailing_list = req.params.get('mailing_list')
    if not email:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            email = req_body.get('email')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')
    if not membership_type:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            membership_type = req_body.get('membership_type')
    if not country:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            country = req_body.get('country')
    if not postal_code:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            postal_code = req_body.get('postal_code')
    if not company:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            company = req_body.get('company')
    if not university:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            university = req_body.get('university')
    if not mailing_list:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            mailing_list = req_body.get('mailing_list')
    if not mailing_list:
        mailing_list = False
    if not membership_type or membership_type != 'complimentary': # For now restrict membership type
        membership_type = 'complimentary'


    status_code = 215
    result = { "error": "unknown error" }
    logging.info("Email: " + email + ", Name: " + name + ", Membership: " + membership_type + ", Country:" + country)
    if email and name and membership_type and helperfuncs.is_force_majeure_country(country):
        email = email.lower()
        customers = stripe.Customer.list(email=email)
        s_customer = None
        metadata = None
        end_date = None
        edate = None
        if len(customers) > 0:
            for customer in customers:
                if customer.email == email:
                    s_customer = customer
                    break
        if s_customer:
            metadata = s_customer.get('metadata', None)
        if metadata:
            end_date = metadata.get('membership_end') #only worred about if has an end date (lifetime member is handled in the create_complimentary_member method)
        if end_date:
            try:
                edate = datetime.strptime(end_date, "%m/%d/%Y")
            except:
                edate = datetime.strptime(end_date, "%Y-%m-%d")
            

        if edate is not None and edate > (datetime.today() + timedelta(30)):
            result = {"error": "You already have a membership."}
            status_code = 214
        else:
            # steps to create member
            fname = name[0: name.find(' ')]
            lname = name[name.find(' ') + 1:]
            
            helperfuncs.create_complimentary_member(fname, lname, email, company, country, postal_code, datetime.today().strftime("%Y-%m-%d"), (datetime.today() + timedelta(364)).strftime("%Y-%m-%d"), membership_type, mailing_list, False)
            try:
                cop = OWASPCopper()
                member = cop.FindPersonByEmailObj(email)
                if member:
                    owasp_email = helperfuncs.get_owasp_email(member[0], cop)
                    helperfuncs.unsuspend_google_user(owasp_email)
                else:
                    logging.warn("No member found in copper")        
            except Exception as err:
                logging.error(f'Failed attempting to find and possibly unsuspend Google email: {err}')
            
            status_code = 200
            result = { "success": "User created."}  
    else:
        result = { "error": f"malformed request : {email}, {name}, {membership_type}" }
    
    return func.HttpResponse(status_code=status_code, body = json.dumps(result))
        
    
