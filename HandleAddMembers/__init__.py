import logging

import azure.functions as func
import csv
import json
import base64
from io import StringIO
from ..SharedCode.helperfuncs import MemberData
import os
import requests
import stripe
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.owaspmailchimp import OWASPMailchimp
from ..SharedCode.copper import OWASPCopper
from ..SharedCode.googleapi import OWASPGoogle

import sendgrid
from sendgrid.helpers.mail import *
from datetime import datetime, timedelta

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    filej = req.params.get('file')
    if not filej:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            filej = req_body.get('file')

    if filej:
        f64part = filej[filej.find('base64,') + 7:]
        fstr = base64.b64decode(f64part).decode(encoding='utf-8')
        results = import_members(fstr)
        mail_results(results)

        return func.HttpResponse("File received.")
    else:
        logging.error("failed to get file from post")
        return func.HttpResponse(
             "Something is not right.",
             status_code=400
        )

def mail_results(results):
    user_email = '[membership@owasp.com]'
    subject = 'Membership Import Results for {datetime.today()}'
    msg = ''
    if len(results) > 0:
        for result in results:
            if msg:
                msg = msg + '\n' + result
            else:
                msg = result                
    else:
        msg = 'There were no results. No memberships were added.'

    from_email = From('noreply@owasp.org', 'OWASP')
    to_email = To(user_email)
    content = Content('text/plain', msg)
    message = Mail(from_email, to_email, subject, content)
    
    try:
        sgClient = sendgrid.SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sgClient.client.mail.send.post(request_body=message.get())
        logging.info(response)
        return True
    except Exception as ex:
        template = "An exception of type {0} occurred while sending an email. Arguments:\n{1!r}"
        err = template.format(type(ex).__name__, ex.args)
        logging.exception(err)
        return False

def customer_with_tags_exists(cop, email, tags):
    exists = False
    persons = cop.FindPersonByEmail(email)
    if persons:
        jperson = json.loads(persons)
        if len(jperson) > 0:
            person = jperson[0]
            curr_tags = cop.GetPersonTags(person['id'])

            for tag in tags:
                exists = tag in curr_tags
                if exists:
                    break

    return exists


# override_lifetime_add_tags is for distinguished lifetime members
def import_members(filestr, override_lifetime_add_tags=False):
    results = []
    file = StringIO(filestr)
    reader = csv.DictReader(file)
    stripe.api_key = os.environ['STRIPE_SECRET']
    cop = OWASPCopper()
                
    for row in reader:
        nstr = f"{row['First Name']} {row['Last Name']}".strip()
        memend = row['membership-end-date'].strip()
        if memend == '':
            start = cop.GetDatetimeHelper(row['membership-start-date'])
            days = 365
            if row['membership-type'] == 'two':
                days = 720

            enddate = start + timedelta(days)
            memend = enddate.strftime('%Y-%m-%d')            

        member = MemberData(nstr, row['Email'].lower(), row['Company'], row['Work Country'], row['Work Zip'], row['membership-start-date'], memend, row['membership-type'], row['membership-recurring'], None)
        customers = stripe.Customer.list(email=member.email)
        stripe_id = None
        tags = row['tags'].split(',') # for stripe purposes these 'tags' are simply true if they exist (for instance, distinguished: true will be the result)
        member.AddTags(tags)
        
        if customer_with_tags_exists(cop, member.email, tags):
            results.append({ member.email : 'Person with these tags exists. Possibly duplicate. Verify and remove tags to continue.'})
            continue

        if len(customers.data) > 0: # exists
            customer_id = customers.data[0].get('id', None)
            metadata = customers.data[0].get('metadata', {})
            stripe_member_type = metadata.get('membership_type')
            if stripe_member_type == 'lifetime' and not override_lifetime_add_tags: #do not update the membership on this person unless told to override
                results.append({ member.email : 'Lifetime membership. This person will not be changed.'})
                continue

            membership_type = member.type
            memberdata = member.GetSubscriptionData()
            memop = cop.FindMemberOpportunity(member.email)
            if memop != None:
                persons = cop.FindPersonByEmail(member.email)
                if persons:
                    jperson = json.loads(persons)
                    if jperson and len(jperson) > 0:
                        person = jperson[0]
                        cpstart = cop.GetCustomFieldHelper(cop.cp_person_membership_start, person['custom_fields'])
                        current_start = datetime.fromtimestamp(cpstart)
                        memberdata['membership_start'] = current_start.strftime('%m/%d/%Y')

            if membership_type and membership_type != 'lifetime': 
                mendstr = metadata.get('membership_end', None) # current membership end say 8/1/2022
                if mendstr != None:
                    mend_dt = datetime.strptime(mendstr, '%m/%d/%Y')
                    #possible case: has membership already...update end date to be +time
                    # This needs to be re-evaluated....
                    if membership_type != 'two':
                        add_days = 365
                    else: 
                        add_days = 730
                    member.end = mend_dt + timedelta(days=add_days)
                    memberdata['membership_end'] = member.end.strftime('%m/%d/%Y')

                    member.UpdateMetadata(customer_id,
                        memberdata
                    )
            else: #lifetime
                memberdata['membership_end'] = ''
                member.UpdateMetadata(customer_id,
                        memberdata
                    )

            # also need to update Copper info here...including creating an opportunity for this (even if $0)
            stripe_id = customer_id #cop.UpdateOWASPMembership(member.stripe_id, member.name, member.email, member.GetSubscriptionData())
        else: # does not exist
            stripe_id = member.CreateCustomer()
        
        if stripe_id != None:
            sub_data = member.GetSubscriptionData()
            if sub_data['membership_type'] != 'lifetime' and sub_data.get('membership_end', None) == None:
                if member.email in results:
                    results[member.email] = results[member.email] + '\nMembership found without an end date. Creating 2000-01-01 end date so it can be searched and fixed'
                else:
                    results.append({ member.email: 'Membership found without an end date. Creating 2000-01-01 end date so it can be searched and fixed' })

                sub_data['membership_end'] = '2000-01-01' # faking this data so we can look it up later and fix it
            monetary_value = 0
            if member.type == 'one':
                monetary_value = 50
            elif member.type == 'two':
                monetary_value = 95

            cop.CreateOWASPMembership(stripe_id, None, member.name, member.email, sub_data, monetary_value, tags)
            mailchimp = OWASPMailchimp()
            mailchimpdata = {
                'name': member.name,
                'first_name': member.first,
                'last_name': member.last,
                'source': 'script import',    
                'purchase_type': 'membership',
                'company': member.company,
                'country': member.country,
                'postal_code': member.postal_code,
                'mailing_list': 'True'                    ''
            }
            for tag in tags:
                if tag == 'distinguished':
                    mailchimpdata['status'] = 'distinguished'

            mailchimp.AddToMailingList(member.email, mailchimpdata , member.GetSubscriptionData(), stripe_id)

        return results