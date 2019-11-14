import logging
import os
import azure.functions as func
import json
import requests
from urllib.parse import unquote_plus
from ..SharedCode import salesforce 
from ..SharedCode import github


def main(msg: func.QueueMessage, context: func.Context) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    data = json.loads(msg.get_body().decode('utf-8'))
    if data['type'] == 'view_submission':
        view_id = data['view']['id']
        values = data['view']['state']['values']
        process_form(values, view_id, context.function_directory)


def process_form(values, view_id, function_directory):
    chapter_name = values["cname-id"]["cname-value"]["value"]
    leader_names = values["leadernames-id"]["leadernames-value"]["value"]
    leader_emails = values["emails-id"]["emails-value"]["value"]
    city = values["city-id"]["city-value"]["value"]
    country = values["country-id"]["country-value"]["value"]
    region = values["region-id"]["region-value"]["selected_option"]["value"]
    
    logging.info("Logging into Salesforce...")
    sf = salesforce.OWASPSalesforce()
    r = sf.Login()

    resString = " Chapter created"
    if not r.ok:
        resString = "Failed to login to salesforce"
    else:
        logging.info(f'Creating chapter...{chapter_name}')
        r = sf.CreateChapter(chapter_name, leader_names, leader_emails, city, country, region)    
        if not r.ok:
            resString = f"Failed to Create Chapter {r.status_code}"
        else:
            cg_json = json.loads(r.text)
            # create the leaders here....
            leaders = leader_names.splitlines()
            emails = leader_emails.splitlines()
            if len(leaders) == len(emails):
                count = 0
                for leader in leaders:
                    email = emails[count]
                    count = count + 1
                    logging.info("Adding chapter leader...")
                    cg_id = ''
                    
                    if 'id' in cg_json.keys:
                        cg_id = cg_json['id']
                    else:
                        cg_id = cg_json['Id']

                    r = sf.AddChapterLeader(leader, email, cg_id)   
                    if not r.ok:
                        resString = f"Failed to add leader { leader } with email { email }."
                        break
            else:
                resString = "Failed due to non matching leader names with emails"

            if resString.find("Failed") < 0:
                logging.info("Creating github repository")
                resString = CreateGithubStructure(chapter_name, function_directory)


    resp = '{"view_id":"' + view_id + '", "view": { "type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"close": {"type": "plain_text","text": "OK","emoji": true}, "blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    resp += chapter_name
    resp += ' ' 
    resp += resString
    resp += '"} }]} }' 
    
    logging.info(resp)
    urldialog = "https://slack.com/api/views.update"
    headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN"]}' }
    r = requests.post(urldialog,headers=headers, data=resp)
    logging.info(r.text)


def CreateGithubStructure(chapter_name, func_dir):
    gh = github.OWASPGitHub()
    r = gh.CreateRepository(chapter_name, gh.GH_REPOTYPE_CHAPTER)
    resString = "Chapter created."
    if not gh.TestResultCode(r.status_code):
        resString = f"Failed to create repository for {chapter_name}. Does it already exist?"
        logging.error(resString + " : " + r.text)
    
    if resString.find("Failed") < 0:
        r = gh.InitializeRepositoryPages(chapter_name, gh.GH_REPOTYPE_CHAPTER, basedir = func_dir)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to send initial files for {chapter_name}."
            logging.error(resString + " : " + r.text)

    if resString.find("Failed") < 0:
        r = gh.EnablePages(chapter_name, gh.GH_REPOTYPE_CHAPTER)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to enable pages for {chapter_name}."
            logging.error(resString + " : " + r.text)

    return resString