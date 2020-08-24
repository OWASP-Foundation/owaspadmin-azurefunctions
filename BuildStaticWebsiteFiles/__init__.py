import datetime
import logging
import json
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import helperfuncs
from ..SharedCode import meetup

import base64

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


def build_leaders_json(gh):
    all_leaders = []
    repos = gh.GetPublicRepositories('www-')
    for repo in repos:
        r = gh.GetFile(repo['name'], 'leaders.md')
        if r.ok:
            doc = json.loads(r.text)
            content = base64.b64decode(doc['content']).decode(encoding='utf-8')
            stype = ''
            if 'www-chapter' in repo['name']:
                stype = 'chapter'
            elif 'www-committee' in repo['name']:
                stype = 'committee'
            elif 'www-project' in repo['name']:
                stype = 'project'
            else:
                continue

            add_to_leaders(repo, content, all_leaders, stype)
    
    r = gh.GetFile('owasp.github.io', '_data/leaders.json')
    sha = ''
    if r.ok:
        doc = json.loads(r.text)
        sha = doc['sha']
    
    r = gh.UpdateFile('owasp.github.io', '_data/leaders.json', json.dumps(all_leaders, ensure_ascii=False, indent = 4), sha)
    if r.ok:
        logging.info('Update leaders json succeeded')
    else:
        logging.error(f'Update leaders json failed: {r.status}')


def build_committee_json(gh):
    repos = gh.GetPublicRepositories('www-committee')
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

def build_project_json(gh):
    # we want to build certain json data files every now and then to keep the website data fresh.
    #for each repository, public, with www-project
    #get name of project, level, and type
    # store in json
    #write json file out to github.owasp.io _data folder
    repos = gh.GetPublicRepositories('www-project')
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

def build_chapter_json(gh):
    # we want to build certain json data files every now and then to keep the website data fresh.
    #for each repository, public, with www-project
    #get name of project, level, and type
    # store in json
    #write json file out to github.owasp.io _data folder
    repos = gh.GetPublicRepositories('www-chapter')
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

def build_inactive_chapters_json(gh):
    repos = gh.GetInactiveRepositories('www-chapter')
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

    repos.sort(key=lambda x: x['name'])
    repos.sort(key=lambda x: x['region'], reverse=True)
   
    sha = ''
    r = gh.GetFile('owasp.github.io', '_data/inactive_chapters.json')
    if gh.TestResultCode(r.status_code):
        doc = json.loads(r.text)
        sha = doc['sha']

    contents = json.dumps(repos)
    r = gh.UpdateFile('owasp.github.io', '_data/inactive_chapters.json', contents, sha)
    if gh.TestResultCode(r.status_code):
        logging.info('Updated _data/inactive_chapters.json successfully')
    else:
        logging.error(f"Failed to update _data/inactive_chapters.json: {r.text}")

def update_chapter_admin_team(gh):
    team_id = gh.GetTeamId('chapter-administration')
    if team_id:
        repos = gh.GetPublicRepositories('www-chapter')
        for repo in repos:
            repoName = repo['name']
            r = gh.AddRepoToTeam(str(team_id), repoName)
            if not r.ok:
                logging.info(f'Failed to add repo: {r.text}')

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

def add_to_events(mue, events, repo):
    
    if len(mue) <= 0 or 'errors' in mue:
        return events
    
    chapter = repo.replace('www-chapter-','').replace('-', ' ')
    chapter = " ".join(w.capitalize() for w in chapter.split())
                
    for mevent in mue:
        event = {}
        today = datetime.datetime.today()
        eventdate = datetime.datetime.strptime(mevent['local_date'], '%Y-%m-%d')
        tdelta = eventdate - today
        if tdelta.days >= 0 and tdelta.days < 30:
            event['chapter'] = chapter
            event['repo'] = repo
            event['name'] = mevent['name']
            event['date'] = mevent['local_date']
            event['time'] = mevent['local_time']
            event['link'] = mevent['link']
            event['timezone'] = mevent['group']['timezone']
            if 'description' in mevent:
                event['description'] = mevent['description']
            else:
                event['description'] = ''
                
            events.append(event)

    return events

def create_chapter_events(gh, mu):
    repos = gh.GetPublicRepositories('www-chapter')
    
    events = []
    for repo in repos:
        if 'meetup-group' in repo and repo['meetup-group']:
            if mu.Login():
                muej = json.loads(mue) = mu.GetGroupEvents(repo['meetup-group'])
                add_to_events(muej, events, repo['name'])
                

    if len(events) <= 0:
        return
        
    r = gh.GetFile('owasp.github.io', '_data/chapter_events.json')
    sha = ''
    if r.ok:
        doc = json.loads(r.text)
        sha = doc['sha']
    
    contents = json.dumps(events)
    r = gh.UpdateFile('owasp.github.io', '_data/chapter_events.json', contents, sha)
    if r.ok:
        logging.info('Updated _data/chapter_events.json successfully')
    else:
        logging.error(f"Failed to update _data/chapter_events.json: {r.text}")


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    if mytimer.past_due:
        logging.info('The timer is past due!')

    gh = github.OWASPGitHub()
    logging.info("Building project json file")
    build_project_json(gh)

    logging.info("Building chapter json file")
    build_chapter_json(gh)
    
    logging.info("Building staff projects and milestones json files")
    helperfuncs.build_staff_project_json(gh)

    logging.info('Updating Chapter Administration Team repositories')
    update_chapter_admin_team(gh)

    logging.info('Updating corp_members.yml sitedata from site.data')
    update_corp_members(gh)

    logging.info('Building committees json file')
    build_committee_json(gh)
    
    logging.info('Building leaders json file')
    build_leaders_json(gh)

    logging.info('Updating chapter events')
    mu = meetup.OWASPMeetup()
    create_chapter_events(gh, mu)

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
