import datetime
import json
import re
import os
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import helperfuncs
from ..SharedCode import meetup
import base64
import logging
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity

def build_groups_jsons(gh, repos):
    committee_repos = []
    project_repos = []
    chapter_repos = []
    event_repos = []

    for repo in repos:
        rname = repo['name']
        if 'www-chapter' in rname:
            chapter_repos.append(repo)
        elif 'www-project' in rname:
            project_repos.append(repo)
        elif 'www-committee' in rname:
            committee_repos.append(repo)
        elif 'www-revent' in rname:
            event_repos.append(repo)

    if len(committee_repos) > 0:
        logging.info('Building committees json file')
        try:
            build_committee_json(committee_repos, gh)
        except Exception as err:
            logging.error(f"Exception building committees json file: {err}")
    
    if len(project_repos) > 0:
        logging.info("Building project json file")
        try:
            build_project_json(project_repos, gh)
        except Exception as err:
            logging.error(f"Exception building project json: {err}")

    if len(chapter_repos) > 0:
        logging.info("Building chapter json file")
        try:
            build_chapter_json(chapter_repos, gh)
        except Exception as err:
            logging.error(f"Exception building chapter json: {err}")

    if len(event_repos) > 0:
        logging.info("Building event json file")
        try:
            build_event_json(event_repos, gh)
        except Exception as err:
            logging.error(f"Exception building event json: {err}")

def build_event_json(repos, gh):
    fmt_str = "%a %b %d %H:%M:%S %Y"
    for repo in repos: #change to use title in project repo.....
        repo['name'] = repo['name'].replace('www-revent-','').replace('-', ' ')
        repo['name'] = " ".join(w.capitalize() for w in repo['name'].split())
        try:
            dobj = datetime.datetime.strptime(repo['created'], fmt_str)
            repo['created'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            dobj = datetime.datetime.strptime(repo['updated'], fmt_str)
            repo['updated'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass

    repos.sort(key=lambda x: x['name'])
    repos.sort(key=lambda x: x['level'], reverse=True)
   
    sha = ''
    r = gh.GetFile('owasp.github.io', '_data/revents.json')
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']

    contents = json.dumps(repos)
    r = gh.UpdateFile('owasp.github.io', '_data/revents.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated _data/events.json successfully')
    else:
        logging.error(f"Failed to update _data/revents.json: {r.text}")

def build_committee_json(repos, gh):
    fmt_str = "%a %b %d %H:%M:%S %Y"
    for repo in repos: #change to use title in project repo.....
        repo['name'] = repo['name'].replace('www-committee-','').replace('-', ' ')
        repo['name'] = " ".join(w.capitalize() for w in repo['name'].split())
        try:
            dobj = datetime.datetime.strptime(repo['created'], fmt_str)
            repo['created'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            dobj = datetime.datetime.strptime(repo['updated'], fmt_str)
            repo['updated'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass

    repos.sort(key=lambda x: x['name'])
    repos.sort(key=lambda x: x['level'], reverse=True)
   
    sha = ''
    r = gh.GetFile('owasp.github.io', '_data/committees.json')
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']

    contents = json.dumps(repos)
    r = gh.UpdateFile('owasp.github.io', '_data/committees.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated _data/committees.json successfully')
    else:
        logging.error(f"Failed to update _data/committees.json: {r.text}")

def build_project_json(repos, gh):
    # we want to build certain json data files every now and then to keep the website data fresh.
    #for each repository, public, with www-project
    #get name of project, level, and type
    # store in json
    #write json file out to github.owasp.io _data folder
    fmt_str = "%a %b %d %H:%M:%S %Y"
    for repo in repos: #change to use title in project repo.....
        repo['name'] = repo['name'].replace('www-project-','').replace('-', ' ')
        repo['name'] = " ".join(w.capitalize() for w in repo['name'].split())
        try:
            dobj = datetime.datetime.strptime(repo['created'], fmt_str)
            repo['created'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            dobj = datetime.datetime.strptime(repo['updated'], fmt_str)
            repo['updated'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass

    repos.sort(key=lambda x: x['name'])
    repos.sort(key=lambda x: x['level'], reverse=True)
   
    sha = ''
    r = gh.GetFile('owasp.github.io', '_data/projects.json')
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']

    contents = json.dumps(repos)
    r = gh.UpdateFile('owasp.github.io', '_data/projects.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated _data/projects.json successfully')
    else:
        logging.error(f"Failed to update _data/projects.json: {r.text}")

def build_chapter_json(repos, gh):
    # we want to build certain json data files every now and then to keep the website data fresh.
    #for each repository, public, with www-project
    #get name of project, level, and type
    # store in json
    #write json file out to github.owasp.io _data folder
    #Thu Sep 12 20:51:21 2019
    fmt_str = "%a %b %d %H:%M:%S %Y"
    mu = meetup.OWASPMeetup()
    mu.Login()
    for repo in repos:
        repo['name'] = repo['name'].replace('www-chapter-','').replace('-', ' ')
        repo['name'] = " ".join(w.capitalize() for w in repo['name'].split())
        try:
            dobj = datetime.datetime.strptime(repo['created'], fmt_str)
            repo['created'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            dobj = datetime.datetime.strptime(repo['updated'], fmt_str)
            repo['updated'] = dobj.strftime("%Y-%m-%d")
        except ValueError:
            pass
        
        ecount = 0
        today = datetime.datetime.today()
        earliest = f"{today.year - 1}-01-01T00:00:00.000"
        if 'meetup-group' in repo:
            estr = mu.GetGroupEvents(repo['meetup-group'], earliest, 'past')
            if estr:
                events = json.loads(estr)
                for event in events:
                    eventdate = datetime.datetime.strptime(event['local_date'], '%Y-%m-%d')
                    tdelta = today - eventdate
                    if tdelta.days > 0 and tdelta.days < 365:
                        ecount = ecount + 1    
        repo['meetings'] = ecount

    repos.sort(key=lambda x: x['name'])
    repos.sort(key=lambda x: x['region'], reverse=True)
   
    sha = ''
    r = gh.GetFile('owasp.github.io', '_data/chapters.json')
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']

    contents = json.dumps(repos, indent=4)
    r = gh.UpdateFile('owasp.github.io', '_data/chapters.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated _data/chapters.json successfully')
    else:
        logging.error(f"Failed to update _data/chapters.json: {r.text}")
def get_repos():
    repos = []
    
    table_service = TableService(account_name=os.environ['STORAGE_ACCOUNT'], account_key=os.environ['STORAGE_KEY'])
    #table_service.create_table(table_name=os.environ['REPOSITORY_TABLE']) #create if it doesn't exist
    results = table_service.query_entities(os.environ['REPOSITORY_TABLE'])
    for result in results:
        repo = json.loads(result['Repo'])
        repos.append(repo)

    return repos

def main(name: str) -> None:
    if name != 'orchestrator':
        logging.warn('Returning from func due to missing str')
        return
        
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    logging.info('BuildSiteFilesTwo function ran at %s', utc_timestamp)
    
    gh = github.OWASPGitHub()
   
    #call get repos like this once because leaders and community events both use it
    repos = get_repos()
    build_groups_jsons(gh, repos)