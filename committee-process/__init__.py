import logging
import os
import azure.functions as func
import json
import requests
from urllib.parse import unquote_plus
from ..SharedCode import salesforce
from ..SharedCode import github
from ..SharedCode import copper
from ..SharedCode import owaspym

def main(msg: func.QueueMessage, context: func.Context) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    data = json.loads(msg.get_body().decode('utf-8'))
    if data['type'] == 'view_submission':
        view_id = data['view']['id']
        values = data['view']['state']['values']
        process_form(values, view_id, context.function_directory)

def process_form(values, view_id, function_directory):
    group_name = values["cname-id"]["cname-value"]["value"]
    leader_names = values["leadernames-id"]["leadernames-value"]["value"]
    leader_emails = values["emails-id"]["emails-value"]["value"]
    leader_githubs = values["github-id"]["github-value"]["value"]

    CreateYourMembershipGroup(group_name)

    leaders = leader_names.splitlines()
    emails = leader_emails.splitlines()
    emaillinks = []
    githubs = leader_githubs.splitlines()

    if len(leaders) == len(emails):
        count = 0
        for leader in leaders:
            email = emails[count]
            count = count + 1
            logging.info("Adding committee leader...")

            emaillinks.append(f'[{leader}](mailto:{email})')

        logging.info("Creating github repository")
        resString = CreateGithubStructure(group_name, function_directory, emaillinks, githubs)
        # do copper integration here
        if not 'Failed' in resString:
            resString = CreateCopperObjects(group_name, leaders, emails, githubs)
    else:
        resString = "Failed due to non matching leader names with emails"

    resp = '{"view_id":"' + view_id + '", "view": { "type": "modal","title": {"type": "plain_text","text": "owaspadmin"},"close": {"type": "plain_text","text": "OK","emoji": true}, "blocks": [{"type": "section","text": {"type": "plain_text","text": "'
    resp += group_name
    resp += ' '
    resp += resString
    resp += '"} }]} }'

    logging.info(resp)
    urldialog = "https://slack.com/api/views.update"
    headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN_GENERAL"]}' }
    r = requests.post(urldialog,headers=headers, data=resp)
    logging.info(r.text)

def CreateCopperObjects(committee_name, leaders, emails, gitusers):
    resString = 'Committee created.'
    cp = copper.OWASPCopper()
    gh = github.OWASPGitHub()
    repo = gh.FormatRepoName(committee_name, gh.RepoType.COMMITTEE)
    committee_name = "Committee - OWASP " + committee_name

    if cp.CreateProject(committee_name, leaders, emails, gitusers, copper.OWASPCopper.cp_project_type_option_committee, copper.OWASPCopper.cp_project_chapter_status_option_active, repo = repo) == '':
        resString = "Failed to create Copper objects"

    return resString

def CreateGithubStructure(project_name, func_dir, emaillinks, githubs):
    gh = github.OWASPGitHub()
    r = gh.CreateRepository(project_name, gh.RepoType.COMMITTEE)
    resString = "Committee created."
    if not r.ok:
        resString = f"Failed to create repository for {project_name}."
        logging.error(resString + " : " + r.text)

    if resString.find("Failed") < 0:
        r = gh.InitializeRepositoryPages(project_name, gh.RepoType.COMMITTEE, basedir = func_dir)
        if not r.ok:
            resString = f"Failed to send initial files for {project_name}."
            logging.error(resString + " : " + r.text)

    if resString.find("Failed") < 0:
        repoName = gh.FormatRepoName(project_name, gh.RepoType.COMMITTEE)
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
        r = gh.EnablePages(project_name, gh.RepoType.COMMITTEE)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to enable pages for {project_name}."
            logging.error(resString + " : " + r.text)

    if resString.find("Failed") < 0:
        repo = gh.FormatRepoName(project_name, gh.RepoType.COMMITTEE)
        added = True
        rtext = ''
        for person in githubs:
            r = gh.AddPersonToRepo(person, repo)
            if not r.ok or r.status_code != 204:
                added = False
                rtext = r.text

        if not added:
            resString = f"Note: Could not add one or more users to repository."
            logging.warn(resString + " : " + rtext)

    return resString


def GetYMRegionType(region):
    region_type = owaspym.OWASPYM.GROUP_TYPE_UNCLASSIFIED
    if region == 'Africa':
        region_type = owaspym.OWASPYM.GROUP_TYPE_AFRICA_CHAPTERS
    elif region == 'Asia':
        region_type = owaspym.OWASPYM.GROUP_TYPE_ASIA_CHAPTERS
    elif 'Caribbean' in region:
        region_type = owaspym.OWASPYM.GROUP_TYPE_CARIBBEAN_CHAPTERS
    elif region == 'Central America':
        region_type = owaspym.OWASPYM.GROUP_TYPE_CENTRAL_AMERICA_CHAPTERS
    elif 'Europe' in region:
        region_type = owaspym.OWASPYM.GROUP_TYPE_EUROPE_CHAPTERS
    elif region == 'North America':
        region_type = owaspym.OWASPYM.GROUP_TYPE_NORTH_AMERICA_CHAPTERS
    elif region == 'Oceania':
        region_type = owaspym.OWASPYM.GROUP_TYPE_OCEANIA_CHAPTERS
    elif region == 'South America':
        region_type = owaspym.OWASPYM.GROUP_TYPE_SOUTH_AMERICA_CHAPTERS

    return region_type

def CreateYourMembershipGroup(group_name):
    ym = owaspym.OWASPYM()
    if ym.Login():
        shortDesc = "OWASP® Committees help the staff and board to create initiatives and manage the domain for which they are formed."
        welcomeContent = "<h2>Welcome</h2><p>Include some information here about your committee</p><br><p>For OWASP policies and how they affect your committee, please see <a href='https://owasp.org/www-policy/operational/'>OWASP Policies</a></p>"
        ym.CreateGroup(ym.GROUP_TYPE_COMMITTEE, group_name, shortDesc, welcomeContent)
