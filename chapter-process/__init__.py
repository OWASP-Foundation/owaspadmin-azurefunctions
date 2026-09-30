import logging
import os
import azure.functions as func
import json
import requests
from urllib.parse import unquote_plus
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
    git_users = ''
    if 'github-id' in values and 'github-value' in values['github-id'] and 'value' in values['github-id']['github-value']:
        git_users = values["github-id"]["github-value"]["value"]
    if git_users == None:
        git_users = ''

    city = values["city-id"]["city-value"]["value"]
    country = values["country-id"]["country-value"]["value"]
    region = values["region-id"]["region-value"]["selected_option"]["value"]
    valid_regions = ['Unknown', 'Africa', 'Asia', 'Central America', 'Europe', 'North America', 'Oceania', 'South America', 'The Caribbean']
    if region not in valid_regions:
        if region == 'North Americ':
            region = 'North America'
        elif region == 'South Americ':
            region = 'South America'
        elif region == 'Europ':
            region = 'Europe'
        elif region == 'Asi':
            region = 'Asia'
        elif region == 'Afric':
            region = 'Africa'
        elif region == 'Oceani':
            region = 'Oceania'
        elif region == 'Central Americ':
            region = 'Central America'
        elif region == 'Caribbea':
            region = 'Caribbean'
        else:
            region = 'Unknown'    

    leaders = leader_names.splitlines()
    emails = leader_emails.splitlines()
    gitusers = git_users.splitlines()

    emaillinks = []

    if len(leaders) == len(emails):
        count = 0
        for leader in leaders:
            email = emails[count]
            count = count + 1
            logging.info("Adding chapter leader...")
            emaillinks.append(f'[{leader}](mailto:{email})')
        logging.info("Creating github repository")
        # not needed, no github now resString = CreateGithubStructure(chapter_name,function_directory, region, emaillinks, gitusers, country)
        # do copper integration here
        if not 'Failed' in resString:
            # Copper is gone
            # resString = CreateCopperObjects(chapter_name, leaders, emails, gitusers, region, country)
            # Needs to upate to OWASPWeb
            # For now do something that is nothing
            email = emails[count]
    else:
        resString = "Failed due to non matching leader names with emails"


    resp = '{"view_id":"' + view_id + '", "view": { "type": "modal","title": {"type": "plain_text","text": "admin_af_app"},"close": {"type": "plain_text","text": "OK","emoji": true}, "blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    resp += chapter_name
    resp += ' '
    resp += resString
    resp += '"} }]} }'

    logging.info(resp)
    urldialog = "https://slack.com/api/views.update"
    headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN_GENERAL"]}' }
    r = requests.post(urldialog,headers=headers, data=resp)
    logging.info(r.text)