import datetime
import logging
import json
import re
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import helperfuncs
from ..SharedCode import meetup
import base64

def build_groups_jsons(gh):
    repos = gh.GetPublicRepositories('www-')
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
            mu = meetup.OWASPMeetup()
            mu.Login()
            estr = mu.GetGroupEvents(repo['meetup-group'], earliest)
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

def update_chapter_admin_team(gh):
    team_id = gh.GetTeamId('chapter-administration')
    if team_id:
        repos = gh.GetPublicRepositories('www-chapter')
        for repo in repos:
            repoName = repo['name']
            r = gh.AddRepoToTeam(str(team_id), repoName)
            if not r.ok:
                logging.info(f'Failed to add repo: {r.text}')

def update_events_sitedata(gh):
    # file from _data/event.yml just needs to go in assets/sitedata/
    r = gh.GetFile('owasp.github.io', '_data/events.yml')

    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        contents = base64.b64decode(doc['content']).decode()
    

        gh = github.OWASPGitHub()
        r = gh.GetFile('owasp.github.io', 'assets/sitedata/events.yml')

        if gh.TestResultCode(r.status_code):
            doc = json.loads(r.text)
            sha = doc['sha']

        r = gh.UpdateFile('owasp.github.io', 'assets/sitedata/events.yml', contents, sha)
        if gh.TestResultCode(r.status_code):
            logging.info('Updated assets/sitedata/events.yml successfully')
        else:
            logging.error(f"Failed to update assets/sitedata/events.yml: {r.text}")
    else:
        logging.error(f'Failed to update assets/sitedata/events.yml: {r.text}')

def update_corp_members(gh):
    # file from _data/corp_members.yml just needs to go in assets/sitedata/
    r = gh.GetFile('owasp.github.io', '_data/corp_members.yml')

    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        contents = base64.b64decode(doc['content']).decode()
    

        gh = github.OWASPGitHub()
        r = gh.GetFile('owasp.github.io', 'assets/sitedata/corp_members.yml')

        if gh.TestResultCode(r.status_code):
            doc = json.loads(r.text)
            sha = doc['sha']

        r = gh.UpdateFile('owasp.github.io', 'assets/sitedata/corp_members.yml', contents, sha)
        if gh.TestResultCode(r.status_code):
            logging.info('Updated assets/sitedata/corp_members.yml successfully')
        else:
            logging.error(f"Failed to update assets/sitedata/corp_members.yml: {r.text}")
    else:
        logging.error(f'Failed to update assets/sitedata/corp_members.yml: {r.text}')

# def create_chapter_events(gh, mu):
#     repos = gh.GetPublicRepositories('www-chapter')
    
#     events = []
#     for repo in repos:
#         if 'meetup-group' in repo and repo['meetup-group']:
#             if mu.Login():
#                 mstr = mu.GetGroupEvents(repo['meetup-group'])
#                 if mstr:
#                     muej = json.loads(mstr)
#                     add_to_events(muej, events, repo['name'])
                

#     if len(events) <= 0:
#         return
        
#     r = gh.GetFile('owasp.github.io', '_data/chapter_events.json')
#     sha = ''
#     if r.ok:
#         doc = json.loads(r.text)
#         sha = doc['sha']
    
#     contents = json.dumps(events, indents=4)
#     r = gh.UpdateFile('owasp.github.io', '_data/chapter_events.json', contents, sha)
#     if r.ok:
#         logging.info('Updated _data/chapter_events.json successfully')
#     else:
#         logging.error(f"Failed to update _data/chapter_events.json: {r.text}")


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    if mytimer.past_due:
        logging.info('The timer is past due!')

    gh = github.OWASPGitHub()
    
    build_groups_jsons(gh)

    logging.info("Building staff projects and milestones json files")
    try:
        helperfuncs.build_staff_project_json(gh)
    except Exception as err:
        logging.error(f"Exception building staff projects json: {err}")

    logging.info('Updating Chapter Administration Team repositories')
    try:
        update_chapter_admin_team(gh)
    except Exception as err:
        logging.error(f"Exception updating Chapter Administration team: {err}")

    logging.info('Updating corp_members.yml sitedata from site.data')
    try:
        update_corp_members(gh)
    except Exception as err:
        logging.error(f"Exception updating corp_members.yml: {err}")
    

    logging.info('Building sitedata/events yml file')
    try:
        update_events_sitedata(gh)
    except Exception as err:
        logging.error(f"Exception building sitedata/events yml: {err}")

    logging.info('BuildStaticWebsiteFiles timer trigger function ran at %s', utc_timestamp)    

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
