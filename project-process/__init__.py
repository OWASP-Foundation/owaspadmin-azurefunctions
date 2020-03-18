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
    project_name = values["cname-id"]["cname-value"]["value"]
    leader_names = values["leadernames-id"]["leadernames-value"]["value"]
    leader_emails = values["emails-id"]["emails-value"]["value"]
    summary = values["summary-id"]["summary-value"]["value"]
    description = values["desc-id"]["desc-value"]["value"]
    roadmap = values["roadmap-id"]["roadmap-value"]["value"]
    license = values["license-id"]["license-value"]["selected_option"]["value"]
    proj_type = values["project-type-id"]["project-type-value"]["selected_option"]["value"]   

    leaders = leader_names.splitlines()
    emails = leader_emails.splitlines()
    emaillinks = []
    if len(leaders) == len(emails):
        count = 0
        for leader in leaders:
            email = emails[count]
            count = count + 1
            logging.info("Adding project leader...")

            emaillinks.append(f'[{leader}](mailto:{email})')
            logging.info("Creating github repository")
            resString = CreateGithubStructure(project_name, function_directory, emaillinks)
    else:
        resString = "Failed due to non matching leader names with emails"

    resp = '{"view_id":"' + view_id + '", "view": { "type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"close": {"type": "plain_text","text": "OK","emoji": true}, "blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    resp += project_name
    resp += ' ' 
    resp += resString
    resp += '"} }]} }' 
    
    logging.info(resp)
    urldialog = "https://slack.com/api/views.update"
    headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN"]}' }
    r = requests.post(urldialog,headers=headers, data=resp)
    logging.info(r.text)


def CreateGithubStructure(project_name, func_dir, emaillinks):
    gh = github.OWASPGitHub()
    r = gh.CreateRepository(project_name, gh.GH_REPOTYPE_PROJECT)
    resString = "Project created."
    if not gh.TestResultCode(r.status_code):
        resString = f"Failed to create repository for {project_name}."
        logging.error(resString + " : " + r.text)
    
    if resString.find("Failed") < 0:
        r = gh.InitializeRepositoryPages(project_name, gh.GH_REPOTYPE_PROJECT, basedir = func_dir)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to send initial files for {project_name}."
            logging.error(resString + " : " + r.text)

    if resString.find("Failed") < 0:
        repoName = gh.FormatRepoName(project_name, gh.GH_REPOTYPE_PROJECT)
        r = gh.GetFile(repoName, 'leaders.md')
        if r.ok:
            doc = json.loads(r.text)
            sha = doc['sha']
            contents = '### Leaders\n'
            for link in emaillinks:
                contents += f'* {link}\n'
            r = gh.UpdateFile(repoName, 'leaders.md', contents, sha)
            if not r.ok:
                resString = f'Failed to update leaders.md file: {r.text}'

    if resString.find("Failed") < 0:
        r = gh.EnablePages(project_name, gh.GH_REPOTYPE_PROJECT)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to enable pages for {project_name}."
            logging.error(resString + " : " + r.text)

    return resString
