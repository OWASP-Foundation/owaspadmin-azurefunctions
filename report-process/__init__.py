from SharedCode.github import OWASPGitHub
import logging
import os
import azure.functions as func
import requests
import json
import base64
import time
from ..SharedCode import spotchk
from ..SharedCode import helperfuncs
from ..SharedCode.copper import OWASPCopper
import stripe
from urllib.parse import unquote_plus
import pathlib
import urllib
import gspread
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

# Function to process reports on the report-queue
# Currently has
#   chapter-report
#   leader-report
#   member-report
#   project-report

REPORT_TYPE_CHAPTER = 0
REPORT_TYPE_MEMBER = 1 # not used as member does not produce a spreadsheet - but will leave it
REPORT_TYPE_LEADER = 2
REPORT_TYPE_PROJECT = 3

def main(msg: func.QueueMessage) -> None:
    datastr = msg.get_body().decode('utf-8')
    
    logging.info('Report queue processed an item: %s',
                 datastr)

    if 'chapter-report' in datastr:
        process_chapter_report(datastr)
    elif 'leader-report' in datastr:
        process_leader_report(datastr)
    elif 'member-report' in datastr:
        process_member_report(datastr)
    elif 'project-report' in datastr:
        process_project_report(datastr)
    else:
        logging.warn('No report to process in item')



def get_repo_name(urlstr):
    sndx = urlstr.find('/www-chapter') + 1
    endx = urlstr.find('/', sndx)

    return urlstr[sndx:endx]

def create_spreadsheet(spreadsheet_name, row_headers, report_type):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(client_secret, scope)
    drive = build('drive', 'v3', credentials=creds, cache_discovery=False)
    
    parents = [os.environ['CHAPTER_REPORT_FOLDER']]
    if report_type == REPORT_TYPE_MEMBER:# not used as member does not produce a spreadsheet - but will leave it
        parents = [os.environ['MEMBER_REPORT_FOLDER']]
    elif report_type == REPORT_TYPE_LEADER:
        parents = [os.enivon['LEADER_REPORT_FOLDER']]
    elif report_type == REPORT_TYPE_PROJECT:
        parents = [os.environ['PROJECT_REPORT_FOLDER']]


    file_metadata = {
        'name': spreadsheet_name,
        'parents': parents,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
    }

    rfile = drive.files().create(body=file_metadata, supportsAllDrives=True).execute()
    file_id = rfile.get('id')

    client = gspread.authorize(creds)
    sheet = client.open(spreadsheet_name).sheet1

    

    sheet.append_row(row_headers)
    header_format = {
        "backgroundColor": {
        "red": 0.0,
        "green": .39,
        "blue": 1.0
        },
        "textFormat": {
        "bold":"true",
        "foregroundColor": {
            "red":1.0,
            "green":1.0,
            "blue":1.0
        }
        }
    }
    sheet.format('A1:Z1', header_format)
    return sheet, file_id

def get_spreadsheet_name(base_name):
    report_name = base_name
    report_date = datetime.now()

    return report_name + ' ' + report_date.strftime('%Y-%m-%d-%H-%M-%S')

def add_member_row(rows, headers, name, email, memtype, memstart, memend):
    row_data = headers.copy()
    for i in range(len(row_data)):
        row_data[i] = ''

    row_data[0] = name
    row_data[1] = email
    row_data[2] = memtype
    row_data[3] = memstart
    row_data[4] = memend
    
    rows.append(row_data)

def add_leader_row(rows, headers, name, email, group, url):
    row_data = headers.copy()
    for i in range(len(row_data)):
        row_data[i] = ''

    row_data[0] = name
    row_data[1] = email
    row_data[2] = group
    row_data[3] = url
    
    rows.append(row_data)

def add_group_row(rows, headers, chname, chupdated, chrepo, chregion, chleaders, chemails):
    row_data = headers.copy()
    for i in range(len(row_data)):
        row_data[i] = ''

    row_data[0] = chname
    row_data[1] = chupdated
    row_data[2] = chrepo
    row_data[3] = chregion
    row_data[4] = chleaders
    row_data[5] = chemails

    rows.append(row_data)

def parse_leaderline(line):
    ename = line.find(']')
    name = line[line.find('[') + 1:line.find(']')]
    email = line[line.find('(', ename) + 1:line.find(')', ename)]
    return name, email

def add_to_leaders(repo, content, all_leaders, stype):
    lines = content.split('\n')
    for line in lines:
        fstr = line.find('[')
        testline = line.lower()
        if(testline.startswith('###') and 'leader' not in testline):
            break
        
        if(line.startswith('*') and fstr > -1 and fstr < 4):
            name, email = parse_leaderline(line)
            leader = {}
            leader['name'] = name
            leader['email'] = email
            leader['group'] = repo['title']
            leader['group-type'] = stype
            leader['group_url'] = repo['url']
            
            all_leaders.append(leader)

def process_leader_report(datastr):
    data = urllib.parse.parse_qs(datastr)
    gh = OWASPGitHub()
    gr = gh.GetFile('owasp.github.io', '_data/leaders.json')
    if gr.ok:
        doc = json.loads(gr.text)
        sha = doc['sha']
        content = base64.b64decode(doc['content']).decode(encoding='utf-8')
        ldr_json = json.loads(content)
        sheet_name = get_spreadsheet_name('leader-report')
        row_headers = ['Name', 'Email', 'Group', 'Group URL']
        ret = create_spreadsheet(sheet_name, row_headers, REPORT_TYPE_LEADER)
        sheet = ret[0]
        file_id = ret[1]
        headers = sheet.row_values(1) # pull them again anyway
        rows = []
        for ldr in ldr_json:
            add_leader_row(rows, headers, ldr['name'], ldr['email'], ldr['group-type'], ldr['group_url'])

        sheet.append_rows(rows)
        msgtext = 'Your leader report is ready at https://docs.google.com/spreadsheets/d/' + file_id
        response_url = data['response_url'][0]
        headers = { 'Content-type':'application/json'}
        msgdata = {
            'text':msgtext,
            'response_type':'ephemeral'
        }
        requests.post(response_url, data=json.dumps(msgdata), headers = headers)

def process_chapter_report(datastr):
    data = urllib.parse.parse_qs(datastr)
    gh = OWASPGitHub()
    gr = gh.GetFile('owasp.github.io', '_data/chapters.json')
    if gr.ok:
        doc = json.loads(gr.text)
        sha = doc['sha']
        content = base64.b64decode(doc['content']).decode(encoding='utf-8')
        ch_json = json.loads(content)
        sheet_name = get_spreadsheet_name('chapter-report')
        row_headers = ['Chapter Name', 'Last Update', 'Repo', 'Region', 'Leaders', 'Emails']
        ret = create_spreadsheet(sheet_name, row_headers, REPORT_TYPE_CHAPTER)
        sheet = ret[0]
        file_id = ret[1]
        headers = sheet.row_values(1) # pull them again anyway
        rows = []
        for ch in ch_json:
            repo = get_repo_name(ch['url'])
            lr = gh.GetFile(repo, 'leaders.md')
            if lr.ok:
                ldoc = json.loads(lr.text)
                lcontent = base64.b64decode(ldoc['content']).decode(encoding='utf-8')
                # need to grab the leaders....
                leaders = []
                leader_emails = []
                add_to_leaders(ch, lcontent, leaders, 'chapter')
                leaderstr = ''
                emailstr = ''
                i = 0
                count = len(leaders)
                for leader in leaders:
                    i+=1
                    leaderstr += leader['name']
                    if leader['email'] is not None and '@' in leader['email']:
                        emailstr += leader['email'].replace('mailto://','').replace('mailto:', '')
                    else:
                        emailstr += 'Unknown'

                    if i < count:
                        leaderstr += ', '
                        emailstr += '\n'

                add_group_row(rows, headers, ch['name'], ch['updated'], repo, ch['region'], leaderstr, emailstr)

        sheet.append_rows(rows)
        msgtext = 'Your chapter report is ready at https://docs.google.com/spreadsheets/d/' + file_id
        response_url = data['response_url'][0]
        headers = { 'Content-type':'application/json'}
        msgdata = {
            'text':msgtext,
            'response_type':'ephemeral'
        }
        requests.post(response_url, data=json.dumps(msgdata), headers = headers)

def process_member_report(datastr):
    data = urllib.parse.parse_qs(datastr)
    stripe.api_key = os.environ['STRIPE_SECRET']
    stripe.api_version = "2020-08-27"

    search = "-metadata['membership_type']:null"

    member_data = {
        'one':0,
        'two':0,
        'lifetime':0,
        'complimentary':0
    }

    customers = stripe.Customer.search(query=search, limit=100)    
    
    for customer in customers.auto_paging_iter():
        mdata = customer.get('metadata', None)
        if mdata:
            member_type = mdata.get('membership_type', None)
            
            if member_type:
                member_type = member_type.lower().strip()

            if member_type and member_type == 'lifetime':
                member_data['lifetime']+=1     
                
            elif member_type and member_type in ['one', 'two', 'complimentary']: # this is a non lifetime member
                member_end = mdata.get('membership_end', None)
                
                if not member_end:
                    print(f"ERROR: No membership end for member {customer['id']} and type {member_type}")
                else:
                    member_end_date = helperfuncs.get_datetime_helper(member_end)                    
                    if not member_end_date:
                        print(f"ERROR: Could not convert member end date for member {customer['id']} and type {member_type}")
                    elif member_end_date >= datetime.today():                                                
                        member_data[member_type]+=1
                       

    total_members = member_data['complimentary'] + member_data['one'] + member_data['two'] + member_data['lifetime']
    msgtext = ""

    msgtext += f"\ttotal members: {total_members}\n"
    msgtext += f"\t\tone: {member_data['one']}\ttwo:{member_data['two']}\n"
    msgtext += f"\t\tlifetime: {member_data['lifetime']}\tcomplimentary:{member_data['complimentary']}\n"

    response_url = data['response_url'][0]
    headers = { 'Content-type':'application/json'}
    msgdata = {
        'text':msgtext,
        'response_type':'ephemeral'
    }
    requests.post(response_url, data=json.dumps(msgdata), headers = headers)

def process_member_report_old(datastr):
    cp = OWASPCopper()
    data = urllib.parse.parse_qs(datastr)
    member_data = {
        'month':0,
        'one':0,
        'two':0,
        'lifetime':0,
        'complimentary':0,
        'student':0,
        'honorary':0
    }

    done = False
    page = 1
    today = datetime.today()

    while(not done):
        retopp = cp.ListOpportunities(page_number=page, status_ids=[1], pipeline_ids=[cp.cp_opportunity_pipeline_id_membership]) # all Won Opportunities for Individual Membership
        if retopp != '':
            opportunities = json.loads(retopp)
            if len(opportunities) < 100:
                logging.debug('listing opportunities done')
                done = True
            for opp in opportunities:                
                end_val = cp.GetCustomFieldValue(opp['custom_fields'], cp.cp_opportunity_end_date)
                if end_val is not None:
                    end_date = datetime.fromtimestamp(end_val)
                    if end_date and end_date < today:
                        continue
                if end_val is None and 'lifetime' not in opp['name'].lower():
                    continue               

                close_date = helperfuncs.get_datetime_helper(opp['close_date'])
                if close_date is None:
                    close_date = datetime.fromtimestamp(opp['date_created'])
                if close_date.month == today.month and close_date.year == today.year:
                    member_data['month'] = member_data['month'] + 1

                # check this doesn't count multiple yearly memberships for one person....
                memtype = 'unknown'
                if 'student' in opp['name'].lower():
                    memtype = 'student'
                    member_data['student'] = member_data['student'] + 1
                elif 'complimentary' in opp['name'].lower():
                    memtype = 'complimentary'
                    member_data['complimentary'] = member_data['complimentary'] + 1
                elif 'honorary' in opp['name'].lower():
                    memtype = 'honorary'
                    member_data['honorary'] = member_data['honorary'] + 1
                elif 'one' in opp['name'].lower(): 
                    memtype = 'one'
                    member_data['one'] = member_data['one'] + 1
                elif 'two' in opp['name'].lower():
                    memtype = 'two'
                    member_data['two'] = member_data['two'] + 1
                elif 'lifetime' in opp['name'].lower():
                    memtype = 'lifetime'
                    member_data['lifetime'] = member_data['lifetime'] + 1
 

            page = page + 1
    
    total_members = member_data['student'] + member_data['complimentary'] + member_data['honorary'] + member_data['one'] + member_data['two'] + member_data['lifetime']
    msgtext = f"\ttotal members: {total_members}\tthis month:{member_data['month']}\n"
    msgtext += f"\t\tone: {member_data['one']}\ttwo:{member_data['two']}\n"
    msgtext += f"\t\tlifetime: {member_data['lifetime']}\tstudent:{member_data['student']}\n"
    msgtext += f"\t\tcomplimentary: {member_data['complimentary']}\thonorary:{member_data['honorary']}\n"
    
    
    response_url = data['response_url'][0]
    headers = { 'Content-type':'application/json'}
    msgdata = {
        'text':msgtext,
        'response_type':'ephemeral'
    }
    requests.post(response_url, data=json.dumps(msgdata), headers = headers)

def process_project_report(datastr):
    data = urllib.parse.parse_qs(datastr)
    gh = OWASPGitHub()
    gr = gh.GetFile('owasp.github.io', '_data/projects.json')
    if gr.ok:
        doc = json.loads(gr.text)
        sha = doc['sha']
        content = base64.b64decode(doc['content']).decode(encoding='utf-8')
        ch_json = json.loads(content)
        sheet_name = get_spreadsheet_name('project-report')
        row_headers = ['Project Name', 'Last Update', 'Repo', 'Level', 'Leaders', 'Emails']
        ret = create_spreadsheet(sheet_name, row_headers, REPORT_TYPE_PROJECT)
        sheet = ret[0]
        file_id = ret[1]
        headers = sheet.row_values(1) # pull them again anyway
        rows = []
        for ch in ch_json:
            repo = get_repo_name(ch['url'])
            lr = gh.GetFile(repo, 'leaders.md')
            if lr.ok:
                ldoc = json.loads(lr.text)
                lcontent = base64.b64decode(ldoc['content']).decode(encoding='utf-8')
                # need to grab the leaders....
                leaders = []
                
                add_to_leaders(ch, lcontent, leaders, 'project')
                leaderstr = ''
                emailstr = ''
                i = 0
                count = len(leaders)
                for leader in leaders:
                    i+=1
                    leaderstr += leader['name']
                    if leader['email'] is not None and '@' in leader['email']:
                        emailstr += leader['email'].replace('mailto://','').replace('mailto:', '')
                    else:
                        emailstr += 'Unknown'

                    if i < count:
                        leaderstr += ', '
                        emailstr += '\n'

                add_group_row(rows, headers, ch['name'], ch['updated'], repo, ch['level'], leaderstr, emailstr)

        sheet.append_rows(rows)
        msgtext = 'Your project report is ready at https://docs.google.com/spreadsheets/d/' + file_id
        response_url = data['response_url'][0]
        headers = { 'Content-type':'application/json'}
        msgdata = {
            'text':msgtext,
            'response_type':'ephemeral'
        }
        requests.post(response_url, data=json.dumps(msgdata), headers = headers)