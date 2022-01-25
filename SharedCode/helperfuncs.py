from datetime import datetime
from datetime import timedelta
from datetime import date
from dateutil import parser
import logging
import json
import azure.functions as func
import base64
import os
import requests
import stripe
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.owaspmailchimp import OWASPMailchimp
from ..SharedCode.copper import OWASPCopper
from ..SharedCode.googleapi import OWASPGoogle
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import Attachment
from sendgrid.helpers.mail import FileContent
from sendgrid.helpers.mail import FileName
from sendgrid.helpers.mail import FileType
from sendgrid.helpers.mail import Disposition

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import From

def get_datetime_helper(datestr):
    retdate = None
    if datestr == None or datestr == '':
        return retdate
        
    try:
        retdate = datetime.strptime(datestr, "%m/%d/%Y")
    except:
        try:
            retdate = datetime.strptime(datestr, "%Y-%m-%d")
        except:
            try:
                retdate = datetime.strptime(datestr, "%m/%d/%y")
            except:
                try:
                    retdate = datetime.fromtimestamp(datestr)
                except:
                    try:
                        retdate = datetime.utcfromtimestamp(datestr)
                    except:
                        pass

    return retdate

def get_owasp_email(member, cp):
    result = ''
    og = OWASPGoogle()

    if member:
        for email in member['emails']:
            if '@owasp.org' in email['email']:
                return email['email']
            else:
                user = og.GetUser(email['email'])
                if user:
                    for email in user['emails']:
                        if '@owasp.org' in email['address']:
                            cp.UpdatePerson(member['id'], other_email=email['address'])
                            return { 'email': email['address'] }

def unsuspend_google_user(owasp_email):
    og = OWASPGoogle()
    user = og.GetUser(owasp_email)
    if user and user['suspended']:
        for email in user['emails']:
            if '@owasp.org' in email['address']:
                if not og.UnsuspendUser(email['address']):
                    logging.warn(f"Failed to unsuspend {email['address']}")

# for leaders, the check should exist in the azure function to not allow 
# complimentary membership if already a member unless within some number 
# of days prior to expiry
# startdate and enddate should be 2020-06-10 format strings
def create_complimentary_member(firstname, lastname, email, company, country, zipcode, startdate, enddate, memtype, mailing_list, is_leader):
    stripe.api_key = os.environ['STRIPE_SECRET']
    cop = OWASPCopper()
    nstr = f"{firstname} {lastname}"                
    leader_agreement = None
    if is_leader:
        leader_agreement = datetime.today().strftime("%m/%d/%Y")
    member = MemberData(nstr, email.lower(), company, country, zipcode, startdate, enddate, memtype, 'no', leader_agreement)
    customers = stripe.Customer.list(email=member.email)
    stripe_id = None
            
    if len(customers.data) > 0: # exists
        customer_id = customers.data[0].get('id', None)
        metadata = customers.data[0].get('metadata', {})
        stripe_member_type = metadata.get('membership_type')
        if stripe_member_type != 'lifetime': #do not update the membership on lifetime members
            membership_type = member.type
            mendstr = metadata.get('membership_end', None)
            if mendstr == None:
                mendstr = enddate
                
            if mendstr != None:
                mend_dt = cop.GetDatetimeHelper(mendstr)
                #possible case: has membership already...update end date to be +time
                if member.end > mend_dt:
                    add_days = 364
                    if membership_type == 'two':
                        add_days = 729
                    
                    member.end = mend_dt + timedelta(days=add_days)
                elif member.end == None: # was not a member, make them one
                    member.end = mend_dt

                if(is_leader):
                    member.UpdateMetadata(customer_id,
                        {
                            "membership_end": member.end.strftime('%m/%d/%Y'),
                            "leader_agreement": datetime.today().strftime("%m/%d/%Y")
                        }
                    )
                else:
                    member.UpdateMetadata(customer_id,
                        {
                            "membership_end": member.end.strftime('%m/%d/%Y'),
                        }
                    )
            
        else: # lifetime-but should never happen here in comp membership
            if(is_leader):
                member.UpdateMetadata(customer_id,
                        {
                            "membership_end": "",
                            "membership_type": "lifetime",
                            "leader_agreement": datetime.today().strftime("%m/%d/%Y")
                        }
                    )
            else:
                member.UpdateMetadata(customer_id,
                        {
                            "membership_end": "",
                            "membership_type": "lifetime"
                        }
                    )
        # also need to update Copper info here...including creating an opportunity for this (even if $0)
        stripe_id = customer_id #cop.UpdateOWASPMembership(member.stripe_id, member.name, member.email, member.GetSubscriptionData())
        
    else: # does not exist
        stripe_id = member.CreateCustomer()
            
    if stripe_id != None:
        cop.CreateOWASPMembership(stripe_id, None, member.name, member.email, member.GetSubscriptionData(), 0.0)
        mailchimp = OWASPMailchimp()
        mailchimpdata = {
            'name': member.name,
            'source': 'script import',    
            'purchase_type': 'membership',
            'company': member.company,
            'country': member.country,
            'postal_code': member.postal_code,
            'mailing_list': mailing_list
        }

        mailchimp.AddToMailingList(member.email, mailchimpdata , member.GetSubscriptionData(), stripe_id)

            
# simple true/false function as opposed to the IsLeaderByEmail Azure Function that returns more details
def is_leader_by_email(email):
    is_leader = False
    if email:
        email = email.lower()
        gh = OWASPGitHub()
        r = gh.GetFile('owasp.github.io', '_data/leaders.json')
        if r.ok:
            doc = json.loads(r.text)
            content = base64.b64decode(doc['content']).decode(encoding='utf-8')
            leaders = json.loads(content)
            is_leader = False
            gleader = {'group_url':'', 'group':''}
            for leader in leaders:
                if email == leader['email']:
                    gleader = leader
                    is_leader = True
                    break

    return is_leader

def send_onetime_secret(emails, secret):
    headers = {
        'Authorization':f"Basic {base64.b64encode((os.environ['OTS_USER'] + ':' + os.environ['OTS_API_KEY']).encode()).decode()}"
    }
    if len(emails) > 0:
        for email in emails:
            logging.info(f"Sending to {email}")
            r = requests.post(f"https://onetimesecret.com/api/v1/share/?secret={secret}&recipient={email}", headers=headers)
            if not r.ok:
                logging.error(f'Failed to send secret: {r.text}')
            else:
                logging.info(f"Secret sent to {email}: {r.text}")
    else:
        logging.error(f"No emails to send")

def get_page_name(content):
    sndx = content.find('title:') + 7
    endx = content.find('\n', sndx)
    return content[sndx:endx]

def get_project_description(content):
    desc = ''
    sndx = content.find('Overview') + 8
    if sndx > -1:
        endx = content.find('##', sndx)
        desc = content[sndx:endx]
        desc = desc.replace('\n','')
        desc = desc.strip()

    return desc

def get_project_leaders(content):
    leaders = []
    
    sndx = content.find('Leadership') + 10
    endx = content.find('##', sndx)
    if sndx == -1:
        return leaders

    leaderstr = content[sndx:endx]
    leaderstr = leaderstr.replace('\n','')
    ldrs = leaderstr.split('*')
    for ldr in ldrs:
        ndx = ldr.find('[')
        if ndx > -1:
            name = ldr[ndx + 1:]
            name = name[:name.find(']'):]
            name = name.replace('- Lead', '')
            mndx = ldr.find('(mailto:')
            mail = ''
            if mndx > -1:
                mail = ldr[mndx + 8:]
                mail = mail[:mail.find(')')]
                mail = mail[:mail.find('?')]
            if name:
                leader = Leader(name, mail)
                leaders.append(leader)

    return leaders

def get_milestone_date(milestone):
    date = ''
    ndx = milestone.find(' ') + 1
    if ndx > -1:
        date = milestone[ndx:ndx + 11] # date must be in format 2020-01-01
        date = date.strip()
        dateparts = []
        if date:
            dateparts = date.split('-')
        try:
            int(dateparts[0])
            int(dateparts[1])
            int(dateparts[2])
        except Exception:
            date = '' #invalid date for milestone
            pass

    return date.strip()

def get_milestone_owner(milestone):
    owner = ''
    milestone = milestone.replace('\n','')
    milestone = milestone.strip()
    ndx = milestone.rfind(']') #aside from \n or spaces this should be the last character
    if ndx == len(milestone) -1:
        sndx = milestone.rfind('[') + 1
        if sndx > 0:
            owner = milestone[sndx:ndx]
            owner = owner.strip()
    lowner = owner.lower()
    if not owner or 'completed' in lowner or 'done' in lowner:
        owner = 'No Owner'

    return owner.strip()

def get_milestone_desc(milestone):
    desc = ''
    sndx = milestone.find(' ') + 1 # start of date
    milestone = milestone.replace('\n','')
    milestone = milestone.strip()
    endx = milestone.rfind(']') #aside from \n or spaces this should be the last character
    if endx == len(milestone) -1:
        endx = milestone.rfind('[') # start of 'owner'
    else:
        endx = len(milestone)

    if sndx > 0 and endx > sndx + 11:
        desc = milestone[sndx + 11:endx]
    desc = desc.strip()
    desc = desc.rstrip(',')
    return desc

def get_milestone_parts(milestone):
    owner = ''
    desc = ''
    date = get_milestone_date(milestone)
    if date:
        owner = get_milestone_owner(milestone)
        desc = get_milestone_desc(milestone)

    return date, owner, desc

def get_milestone_status(datestr):
    status = 'on-time'
    d = parser.parse(datestr).date()
    td = date.today()
    delta = d - td
    if delta.days <= -1:
        status = 'overdue'
    elif delta.days > 30:
        status = 'future'


    return status

def get_project_milestones(content, pname):
    milestones = []
    sndx = content.find('Milestones') + 10
    endx = content.find('##', sndx)
    if sndx == -1:
        return milestones

    milestr = content[sndx:endx]
    milestr = milestr.replace('\n','')
    milestr = milestr.replace('- [', '* [')
    
    if not milestr.startswith('*'):
        milestr = milestr.replace('[ ]', '* [ ]')
        milestr = milestr.replace('[x]', '* [x]')

    mls = milestr.split('*')
    for ms in mls:
        if '[x]' in ms:
            continue
        ms = ms.replace('[ ]', '')
        date, owner, desc = get_milestone_parts(ms)
        if date:
            milestone = Milestone(date)
            milestone.owner = owner
            milestone.description = desc
            milestone.project_name = pname
            milestone.status = get_milestone_status(date)
            milestones.append(milestone)
                    
    return milestones

def build_staff_milestone_json(gh, projects):
    milestones = []
    for project in projects:
        for milestone in project.milestones:
            milestones.append(milestone)

    milestones.sort(key=lambda x: x.milestone_date)
    contents = json.dumps(milestones, default=lambda x: x.__dict__, indent=4)
    r = gh.GetFile('www-staff', '_data/milestones.json')
    sha = ''
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']
    r = gh.UpdateFile('www-staff', '_data/milestones.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated www-staff/_data/milestones.json successfully')
    else:
        logging.error(f"Failed to update www-staff/_data/milestones.json: {r.text}")

def build_staff_project_json(gh):
    repo = 'www-staff'
    path = 'projects'

    files = []
    r, rfiles = gh.GetFilesMatching(repo, path, '')
    if gh.TestResultCode(r.status_code):
        files = files + rfiles
    else: 
        logging.error(f'Failed to get files: {r.text}')
        
    projects = []
    for pfile in files:
        if '-template.md' in pfile:
            continue
        r = gh.GetFile('www-staff', f'projects/{pfile}')
        sha = ''
        if gh.TestResultCode(r.status_code):
            doc = json.loads(r.text)
            content = base64.b64decode(doc['content']).decode()
            name = get_page_name(content)
            if name:
                project = StaffProject(get_page_name(content))
                project.url = f"https://owasp.org/www-staff/projects/{pfile.replace('.md','')}"
                project.description = get_project_description(content)
                project.leaders = get_project_leaders(content)
                project.milestones = get_project_milestones(content, project.name)
                projects.append(project)
        else:
            logging.error(f'Failed to get {pfile}:{r.text}')

    contents = json.dumps(projects, default=lambda x: x.__dict__, indent=4)
    
    build_staff_milestone_json(gh, projects)

    r = gh.GetFile('www-staff', '_data/projects.json')
    sha = ''
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']
    r = gh.UpdateFile('www-staff', '_data/projects.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated www-staff/_data/projects.json successfully')
    else:
        logging.error(f"Failed to update www-staff/_data/projects.json: {r.text}")


def send_notification(user_email, day):
    template_id = None
    if day == 1:
        template_id = os.environ.get('SG_MEMBER_TEMPLATE_1_DAY')
    elif day == 7:
        template_id = os.environ.get('SG_MEMBER_TEMPLATE_7_DAY')
    elif day == 15:
        template_id = os.environ.get('SG_MEMBER_TEMPLATE_15_DAY')
    else:
        logging.exception('SendGrid message not found')
        return False
    
    message = Mail(
        from_email=From('noreply@owasp.org', 'OWASP'),
        to_emails=user_email,
        html_content='<strong>Email Removal</strong>')
    message.template_id = template_id
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
        return True
    except Exception as ex:
        template = "An exception of type {0} occurred while sending an email. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        return False

class Leader:
    def __init__(self, name, email):
        self.name = name
        self.email = email

class Milestone:
    def __init__(self, strdate):
        self.milestone_date = strdate
        self.description = ''
        self.owner = ''
        self.project_name = ''

    def SetDescription(self, desc):
        self.description = desc

    def SetOwner(self, owner):
        self.owner = owner

    def SetProjectName(self, pname):
        self.project_name = pname

class StaffProject:
    def __init__(self, name):
        self.name = name
        self.milestones = []
        self.description = ''
        self.leaders = []
        self.url = ''

    def AddMilestone(self, milestone):
        milestone.SetProjectName(self.name)
        self.milestones.append(milestone)

    def AddLeader(self, leader):
        self.leaders.append(leader)

    def SetDescription(self, desc):
        self.description = desc

    def SetUrl(self, url):
        self.url = url

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

class MemberData:
    def __init__(self, name, email, company, country, postal_code, start, end, type, recurring, leader_agreement):
        self.name = name
        self.first = ''
        self.last = ''
        self.CreateFirstAndLast()

        copper = OWASPCopper()

        self.email = email
        self.company = company
        self.country = country
        self.postal_code = postal_code
        self.leader_agreement = None
        if leader_agreement:
          self.leader_agreement = leader_agreement

        if end:
            self.end = copper.GetDatetimeHelper(end)
        else: 
            self.end = None

        self.start = None
        self.tags = []
        
        start_set = None
        #Should pull start date from copper if it exists
        persons = copper.FindPersonByEmailObj(email)
        if len(persons) > 0: 
            person = persons[0]
            stts = copper.GetCustomFieldHelper(copper.cp_person_membership_start, person['custom_fields'])
            if stts:
                start_set = datetime.fromtimestamp(stts)

        if not start_set: # if copper did not have it, pull it from Stripe
            customers = stripe.Customer.list(email=email)
            if len(customers.data) > 0:
                customer = customers.data[0]
                cmetadata = customer.get('metadata', None)
                if cmetadata:
                    memstart = cmetadata.get('membership_start', None)
                    if memstart:
                        startstr = memstart # don't change a start date
                        if startstr:
                            start_set = copper.GetDatetimeHelper(startstr)
        
        if not start_set: # still no start...
            start_set = copper.GetDatetimeHelper(start)

        self.start = start_set  
        self.type = type
        self.recurring = recurring
        self.stripe_id = None


    @classmethod
    def LoadMemberDataByEmail(self, email):
        # do some stuff
        member_data = None
        copper = OWASPCopper()
        persons = copper.FindPersonByEmailObj(email)
        use_person, use_customer, use_metadata = self.GetPersonCustomerAndMetadata(copper, persons)

        if use_person and use_customer and use_metadata:
            first_email = use_customer.get('email')
            member_data = MemberData(use_person['first_name'] + ' ' + use_person['last_name'], first_email.lower(), use_customer.get('company', None), use_customer.get('country', None), use_customer.get('postal_code', None), use_metadata.get('membership_start', None), use_metadata.get('membership_end', None), use_metadata.get('membership_type', None), use_metadata.get('membership_recurring'), None)
            member_data.AddEmails(use_person['emails'])
        elif use_person: # there is a Copper person but no Stripe customer, not a member
            first_email = use_person['emails'][0]['email']
            company = use_person['company_name']
            country = None
            if 'address' in use_person and 'country' in use_person['address']:
                country = use_person['address']['country']
            postal_code = None
            if 'address' in use_person and 'postal_code' in use_person['address']:
                country = use_person['address']['postal_code']
            member_data = MemberData(use_person['first_name'] + ' ' + use_person['last_name'], first_email.lower(), company, country, postal_code, None, None, None, None)
            member_data.AddEmails(use_person['emails'])
        return member_data

    @classmethod
    def LoadMemberDataByName(self, name):
        member_data = None
        copper = OWASPCopper()
        persons = copper.FindPersonByNameObj(name)
        use_person, use_customer, use_metadata = self.GetPersonCustomerAndMetadata(copper, persons)

        if use_person and use_customer and use_metadata:
            first_email = use_customer.get('email')
            member_data = MemberData(use_person['first_name'] + ' ' + use_person['last_name'], first_email.lower(), use_customer.get('company', None), use_customer.get('country', None), use_customer.get('postal_code', None), use_metadata.get('membership_start', None), use_metadata.get('membership_end', None), use_metadata.get('membership_type', None), use_metadata.get('membership_recurring'), None)
            member_data.AddEmails(use_person['emails'])

        return member_data
        return

    def GetPersonCustomerAndMetadata(copper, persons):
        use_metadata = None
        use_customer = None
        use_person = None
        stripe.api_key = os.environ['STRIPE_SECRET']
        if persons and len(persons) == 1:
            for person in persons:
                use_person = person
                if len(person['emails']) > 0: # do not need people we have no email for
                    for email in person['emails']:
                        customers = stripe.Customer.list(email=email['email'])                       
                        for customer in customers:
                            metadata = customer.get('metadata', None)
                            if metadata.get('membership_type', None) == 'lifetime': # only one that matters...use this
                                use_metadata = metadata
                                use_customer = customer
                                break
                            elif metadata.get('membership_type', None) and metadata.get('membership_end', None):
                                if not use_metadata:
                                    use_metadata = metadata
                                    use_customer = customer
                                else:
                                    memend = copper.GetDatetimeHelper(metadata.get('membership_end', None))
                                    currend = copper.GetDatetimeHelper(use_metadata.get('membership_end', None))
                                    if memend > currend:
                                        use_metadata = metadata
                                        use_customer = customer
                else:
                    raise MemberEmailException("No email address for person")
        elif len(persons) > 1:
            raise MemberCountException("Found more than 1 person. Narrow results.")
        
        return use_person, use_customer, use_metadata

    def CreateFirstAndLast(self):
        names = self.name.split(' ')

        for name in names:
            if not self.first:
                self.first = name
            else:
                self.last = self.last + name + ' '
        
        self.last = self.last.strip()

    def AddEmails(self, emails):
        self.other_emails = []
        for email in emails:
            if email['email'].lower() != self.email:
                self.other_emails.append(email['email'].lower())

    def UpdateMetadata(self, customer_id, metadata):
        self.stripe_id = customer_id
        stripe.Customer.modify(
                            customer_id,
                            metadata=metadata
                        )

    def AddTags(self, tags):
        self.tags = tags

    def CreateCustomer(self):
        mdata = self.GetSubscriptionData()
        for tag in self.tags:
            mdata[tag] = True

        cust = stripe.Customer.create(email=self.email, 
                                       name=self.name,
                                       metadata = mdata)
        
        
        self.stripe_id = cust.get('id')
        return self.stripe_id

    def GetSubscriptionData(self):
        mstart = None
        mend = None
        if self.start:
            mstart = datetime.strftime(self.start, '%m/%d/%Y')
        if self.end:
            mend = datetime.strftime(self.end, '%m/%d/%Y')
        metadata = {
                    'membership_type':self.type,
                    'membership_start':mstart,
                    'membership_end':mend,
                    'membership_recurring':self.recurring,
                    'company':self.company,
                    'country':self.country
                }
        for tag in self.tags:
            metadata[tag] = True

        if(self.leader_agreement):
            metadata['leader_agreement'] = self.leader_agreement

        return metadata

class MemberEmailException(Exception):
  def __init__(self, message):
    self.message = message

class MemberCountException(Exception):
  def __init__(self, message):
    self.message = message