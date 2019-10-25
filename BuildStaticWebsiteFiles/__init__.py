import datetime
import logging
import json
import azure.functions as func
from ..SharedCode import github

def build_project_json():
    # we want to build certain json data files every now and then to keep the website data fresh.
    #for each repository, public, with www-project
    #get name of project, level, and type
    # store in json
    #write json file out to github.owasp.io _data folder
    gh = github.OWASPGitHub()
    repos = gh.GetPublicRepositories('www-project')
    
    for repo in repos:
        repo['name'] = repo['name'].replace('www-project-','').replace('-', ' ')
        repo['name'] = " ".join(w.capitalize() for w in repo['name'].split())

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

def build_chapter_json():
    # we want to build certain json data files every now and then to keep the website data fresh.
    #for each repository, public, with www-project
    #get name of project, level, and type
    # store in json
    #write json file out to github.owasp.io _data folder
    gh = github.OWASPGitHub()
    repos = gh.GetPublicRepositories('www-chapter')
    
    for repo in repos:
        repo['name'] = repo['name'].replace('www-chapter-','').replace('-', ' ')
        repo['name'] = " ".join(w.capitalize() for w in repo['name'].split())

    repos.sort(key=lambda x: x['name'])
    repos.sort(key=lambda x: x['region'], reverse=True)
   
    sha = ''
    r = gh.GetFile('owasp.github.io', '_data/chapters.json')
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']

    contents = json.dumps(repos)
    r = gh.UpdateFile('owasp.github.io', '_data/chapters.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated _data/chapters.json successfully')
    else:
        logging.error(f"Failed to update _data/chapters.json: {r.text}")

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info("Building project json file")
    build_project_json()

    logging.info("Building chapter json file")
    build_chapter_json()
    

    logging.info('BuildStaticWebsiteFiles timer trigger function ran at %s', utc_timestamp)