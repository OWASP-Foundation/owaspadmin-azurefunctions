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

    CreateYourMembershipGroup(chapter_name, region)

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
        resString = CreateGithubStructure(chapter_name,function_directory, region, emaillinks, gitusers, country)
        # do copper integration here
        if not 'Failed' in resString:
            resString = CreateCopperObjects(chapter_name, leaders, emails, gitusers, region, country)

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

def GetCopperRegion(region):
    cp_region = None
    if 'North' in region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_northamerica
    elif 'South' in region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_southamerica
    elif 'Central' in region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_centralamerica
    elif 'Oceania' == region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_oceania
    elif 'Asia' == region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_asia
    elif 'Africa' == region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_africa
    elif 'European' in region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_european_union
    elif 'Eastern' in region:
         cp_region = copper.OWASPCopper.cp_project_chapter_region_option_eastern_europe
    elif 'Caribbean' in region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_the_caribbean
    elif 'Middle' in region:
        cp_region = copper.OWASPCopper.cp_project_chapter_region_option_middle_east

    return cp_region

def CreateCopperObjects(chapter_name, leaders, emails, gitusers, region, country):
    resString = 'Chapter created.'
    cp = copper.OWASPCopper()
    cp_region = GetCopperRegion(region)
    gh = github.OWASPGitHub()
    repo = gh.FormatRepoName(chapter_name, gh.RepoType.CHAPTER)
    chapter_name = "Chapter - OWASP " + chapter_name

    if cp.CreateProject(chapter_name, leaders, emails, gitusers, copper.OWASPCopper.cp_project_type_option_chapter, copper.OWASPCopper.cp_project_chapter_status_option_active, cp_region, country=country, repo = repo) == '':
        resString = "Failed to create Copper objects"

    return resString

def CreateGithubStructure(chapter_name, func_dir, region, emaillinks, gitusers, country):
    gh = github.OWASPGitHub()
    r = gh.CreateRepository(chapter_name, gh.RepoType.CHAPTER)
    resString = "Chapter created."
    if not gh.TestResultCode(r.status_code):
        resString = f"Failed to create repository for {chapter_name}. Does it already exist?"
        logging.error(resString + " : " + r.text)

    if resString.find("Failed") < 0:
        r = gh.InitializeRepositoryPages(chapter_name, gh.RepoType.CHAPTER, basedir = func_dir, region=region, country=country)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to send initial files for {chapter_name}."
            logging.error(resString + " : " + r.text)

    repoName = gh.FormatRepoName(chapter_name, gh.RepoType.CHAPTER)

    if resString.find("Failed") < 0 and len(gitusers) > 0:
        for user in gitusers:
            gh.AddPersonToRepo(user, repoName)

    if resString.find("Failed") < 0:
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
        r = gh.EnablePages(chapter_name, gh.RepoType.CHAPTER)
        if not gh.TestResultCode(r.status_code):
            resString = f"Warning: Could not enable pages for {chapter_name}."
            logging.warn(f"{resString} - {r.text}")

    if not 'Failed' in resString:
        r = gh.AddRepoToTeam('chapter-administration', repoName)
        if not r.ok:
            logging.warn(f'Warning: Could not add team to repo: {r.text}')

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

def CreateYourMembershipGroup(chapter_name, region):
    region_type = GetYMRegionType(region)
    ym = owaspym.OWASPYM()
    if ym.Login():
        shortDesc = "OWASP® Local Chapters build community for application security professionals around the world. Our Local Chapter Meetings are free and open to anyone to attend so both members and non-members are always welcomed."
        welcomeContent = "<h2>Welcome</h2><p>Include some information here about your chapter</p><br><p>For OWASP policies and how they affect your chapter, please see <a href='https://owasp.org/www-policy/operational/'>OWASP Policies</a><br>For help or guidance with your chapter see the <a href='https://owasp.org/www-committee-chapter/'>Chapter Committee</a></p>"
        ym.CreateGroup(region_type, chapter_name, shortDesc, welcomeContent)
