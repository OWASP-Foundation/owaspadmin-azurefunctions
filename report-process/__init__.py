from SharedCode.github import OWASPGitHub
import logging
import os
import azure.functions as func
import requests
import json
import base64
from ..SharedCode import spotchk
from ..SharedCode import helperfuncs
from urllib.parse import unquote_plus
import pathlib
import urllib
import gspread
from datetime import datetime
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

# Function to process reports on the report-queue
# Currently has
#   chapter-report
#   leader-report

def main(msg: func.QueueMessage) -> None:
    datastr = msg.get_body().decode('utf-8')
    
    logging.info('Report queue processed an item: %s',
                 datastr)

    if 'chapter-report' in datastr:
        process_chapter_report(datastr)
    elif 'leader-report' in datastr:
        process_leader_report(datastr)
    else:
        logging.warn('No report to process in item')



def get_repo_name(urlstr):
    sndx = urlstr.find('/www-chapter') + 1
    endx = urlstr.find('/', sndx)

    return urlstr[sndx:endx]

def create_spreadsheet(spreadsheet_name, row_headers):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(client_secret, scope)
    drive = build('drive', 'v3', credentials=creds, cache_discovery=False)
    

    file_metadata = {
        'name': spreadsheet_name,
        'parents': [os.environ['CHAPTER_REPORT_FOLDER']],
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


def add_leader_row(rows, headers, name, email, group, url):
    row_data = headers.copy()
    for i in range(len(row_data)):
        row_data[i] = ''

    row_data[0] = name
    row_data[1] = email
    row_data[2] = group
    row_data[3] = url
    
    rows.append(row_data)

def add_chapter_row(rows, headers, chname, chupdated, chrepo, chregion, chleaders):
    row_data = headers.copy()
    for i in range(len(row_data)):
        row_data[i] = ''

    row_data[0] = chname
    row_data[1] = chupdated
    row_data[2] = chrepo
    row_data[3] = chregion
    row_data[4] = chleaders

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
        ret = create_spreadsheet(sheet_name, row_headers)
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
        row_headers = ['Chapter Name', 'Last Update', 'Repo', 'Region', 'Leaders']
        ret = create_spreadsheet(sheet_name, row_headers)
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
                add_to_leaders(ch, lcontent, leaders, 'chapter')
                leaderstr = ''
                i = 0
                count = len(leaders)
                for leader in leaders:
                    i+=1
                    leaderstr += leader['name']
                    if i < count:
                        leaderstr += ', '

                add_chapter_row(rows, headers, ch['name'], ch['updated'], repo, ch['region'], leaderstr)

        sheet.append_rows(rows)
        msgtext = 'Your chapter report is ready at https://docs.google.com/spreadsheets/d/' + file_id
        response_url = data['response_url'][0]
        headers = { 'Content-type':'application/json'}
        msgdata = {
            'text':msgtext,
            'response_type':'ephemeral'
        }
        requests.post(response_url, data=json.dumps(msgdata), headers = headers)