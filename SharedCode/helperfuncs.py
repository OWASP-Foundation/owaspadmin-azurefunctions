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
                    pass

    return retdate

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
            if mendstr != None:
                mend_dt = datetime.strptime(mendstr, '%m/%d/%Y')
                #possible case: has membership already...update end date to be +time
                if member.end > mend_dt:
                    add_days = 364
                    if membership_type == 'two':
                        add_days = 729
                        member.end = mend_dt + timedelta(days=add_days)

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
        self.email = email
        self.company = company
        self.country = country
        self.postal_code = postal_code
        self.leader_agreement = None
        if leader_agreement:
          self.leader_agreement = leader_agreement

        try:
            self.start = datetime.strptime(start, "%Y-%m-%d")
        except:
            self.start = datetime.strptime(start, "%m/%d/%Y")
        try:
            self.end = datetime.strptime(end, "%Y-%m-%d")
        except:
            self.end = datetime.strptime(end, "%m/%d/%Y")
            
        self.type = type
        self.recurring = recurring
        self.stripe_id = None
    def UpdateMetadata(self, customer_id, metadata):
        self.stripe_id = customer_id
        stripe.Customer.modify(
                            customer_id,
                            metadata=metadata
                        )
    def CreateCustomer(self):
        metadata = {
                                           'membership_type':self.type,
                                           'membership_start':datetime.strftime(self.start, '%m/%d/%Y'),
                                           'membership_end':datetime.strftime(self.end, '%m/%d/%Y'),
                                           'membership_recurring':self.recurring,
                                           'company':self.company,
                                           'country':self.country,
                                       }
        if self.leader_agreement:
            metadata['leader_agreement'] = self.leader_agreement

        cust = stripe.Customer.create(email=self.email, 
                                       name=self.name,
                                       metadata = metadata)
        
        
        self.stripe_id = cust.get('id')
        return self.stripe_id

    def GetSubscriptionData(self):
        metadata = {
                    'membership_type':self.type,
                    'membership_start':datetime.strftime(self.start, '%Y-%m-%d'),
                    'membership_end':datetime.strftime(self.end, '%Y-%m-%d'),
                    'membership_recurring':self.recurring,
                    'company':self.company,
                    'country':self.country,
                }
        if(self.leader_agreement):
            metadata['leader_agreement'] = self.leader_agreement

        return metadata