import datetime
import json
import re
import os
import time
import random
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import helperfuncs
from ..SharedCode import meetup
import base64
import logging
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity


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
            estr = mu.GetGroupEvents(repo['meetup-group'], earliest=earliest, status='past')
            if estr:
                event_json = json.loads(estr)
                if event_json and event_json['data'] and event_json['data']['proNetworkByUrlname']:
                    events = event_json['data']['proNetworkByUrlname']['eventsSearch']['edges']
                
                    for event in events:
                        try:
                            eventdate = datetime.datetime.strptime(event['node']['dateTime'][:10], '%Y-%m-%d')
                            tdelta = today - eventdate
                            if tdelta.days > 0 and tdelta.days < 365:
                                ecount = ecount + 1    
                        except:
                            pass
                    
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

def parse_leaderline(line):
    ename = line.find(']')
    name = line[line.find('[') + 1:line.find(']')]
    email = line[line.find('(', ename) + 1:line.find(')', ename)]
    email = email.lower()
    return name, email

def add_to_leaders(repo, content, all_leaders, stype):
    lines = content.split('\n')
    max_leaders = 5
    leader_count = 0
    in_leaders = False
    for line in lines:
        testline = line.strip()
        if in_leaders and leader_count > 0 and not testline.startswith('*'):
            break
        
        if(testline.startswith('###') and 'leader' not in testline.lower()):
            break
        elif testline.startswith('###') and 'leader' in testline.lower():
            in_leaders = True
            continue

        fstr = testline.find('[')
        if((testline.startswith('-') or testline.startswith('*')) and fstr > -1 and fstr < 4):
            name, email = parse_leaderline(testline)
            if 'leader.email@owasp.org' not in email and leader_count < max_leaders: # default
                leader = {}
                leader['name'] = name
                leader['email'] = email.replace('mailto://', '').replace('mailto:','').lower()
                leader['group'] = repo['title'].replace("\"", "" )
                leader['group-type'] = stype
                leader['group_url'] = repo['url']
                
                all_leaders.append(leader)
                leader_count = leader_count + 1

def build_leaders_json(gh, repos):
    all_leaders = []
    #repos = gh.GetPublicRepositories('www-')
    for repo in repos:
        stype = ''
        # Temporarily suspend this check for testing purposes
        #if repo['name'] == 'www-projectchapter-example':
        #    continue
        
        if 'www-chapter' in repo['url']:
            stype = 'chapter'
        elif 'www-committee' in repo['url']:
            stype = 'committee'
        elif 'www-project' in repo['url']:
            stype = 'project'
        elif 'www-revent' in repo['url']:
            stype = 'event'
        else:
            continue

        #logging.info(f"attempting to get leader file for {repo['name']}")
        r = gh.GetFile(repo['name'], 'leaders.md')
        if r.ok:
            doc = json.loads(r.text)
            content = base64.b64decode(doc['content']).decode(encoding='utf-8')

            add_to_leaders(repo, content, all_leaders, stype)
    
    #logging.info("Getting leaders file in main website....")
    r = gh.GetFile('owasp.github.io', '_data/leaders.json')
    sha = ''
    if r.ok:
        doc = json.loads(r.text)
        sha = doc['sha']
    #logging.info("Updating leaders file in main website....")
    r = gh.UpdateFile('owasp.github.io', '_data/leaders.json', json.dumps(all_leaders, ensure_ascii=False, indent=4), sha)
    if r.ok:
        logging.info('Update leaders json succeeded')
    else:
        logging.error('Update leaders json failed: %s', r.status)

def build_inactive_chapters_json(gh, repos):
    #repos = gh.GetInactiveRepositories('www-chapter') No longer in use, use repo['build'] == 'no pages' to mean inactive
    fmt_str = "%a %b %d %H:%M:%S %Y"
    for repo in repos:
        if repo['build'] != 'no pages': # has a build status
            continue

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

def deEmojify(text):
    EMOJI_PATTERN = re.compile(
        "(["
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251" 
        "])"
    )

    return EMOJI_PATTERN.sub(u'', text)

def add_to_events(mue, events, repo):
    
    #eventdate = datetime.datetime.strptime(event['node']['dateTime'][:10], '%Y-%m-%d')

    if len(mue) <= 0 or 'errors' in mue:
        return events
    
    group = repo.replace('www-chapter-','').replace('www-project-','').replace('www-committee-','').replace('www-revent-','').replace('-', ' ')
    group = " ".join(w.capitalize() for w in group.split())
                
    for mevent in mue:
        event = {}
        today = datetime.datetime.today()
        eventdate = datetime.datetime.strptime(mevent['node']['dateTime'][:10], '%Y-%m-%d')
        tdelta = eventdate - today
        if tdelta.days >= -1 and tdelta.days <= 30:
            event['group'] = group
            event['repo'] = repo
            event['name'] = mevent['node']['title']
            event['date'] = mevent['node']['dateTime'][:10]
            event['time'] = mevent['node']['dateTime'][12:]
            event['link'] = mevent['node']['eventUrl']
            event['timezone'] = mevent['node']['timezone']
            if mevent['node']['description']:
                event['description'] = deEmojify(mevent['node']['description'])
            else:
                event['description'] = ''
                
            events.append(event)

    return events

def create_community_events(gh, mu, repos):
    #repos = gh.GetPublicRepositories('www-')
    
    events = []
    edate = datetime.datetime.today() + datetime.timedelta(-30)
    earliest = edate.strftime('%Y-%m-')+"01T00:00:00.000"
    if mu.Login():
        for repo in repos:
            rname = repo['name']
            if 'www-chapter-' not in rname and 'www-project-' not in rname and 'www-committee-' not in rname and 'www-revent-' not in rname:
                continue

            if 'meetup-group' in repo and repo['meetup-group']:
                # Meetup throttling is likely occuring. We should slow these down....
                mstr = mu.GetGroupEvents(repo['meetup-group'], earliest)
                time.sleep(0 + random.randint(0, 2))
                if mstr:
                    muej = json.loads(mstr)
                    if muej and muej['data'] and muej['data']['proNetworkByUrlname']:
                        mue_events = muej['data']['proNetworkByUrlname']['eventsSearch']['edges']
                        add_to_events(mue_events, events, rname)

    if len(events) <= 0:
        return
        
    r = gh.GetFile('www-community', '_data/community_events.json')
    sha = ''
    if r.ok:
        doc = json.loads(r.text)
        sha = doc['sha']
    
    contents = json.dumps(events, indent=4)
    r = gh.UpdateFile('www-community', '_data/community_events.json', contents, sha)
    if r.ok:
        logging.info('Updated _data/community_events.json successfully')
    else:
        logging.error(f"Failed to update _data/community_events.json: {r.text}")


def update_chapter_admin_team(gh):
    repos = gh.GetPublicRepositories('www-chapter-')
    team_repos = gh.GetTeamRepos("chapter-administration")
    for repo in repos:
        if repo['name'] not in team_repos:
            repoName = repo['name']
            r = gh.AddRepoToTeam("chapter-administration", repoName)
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

def get_repos():
    repos = []
    
    table_service = TableService(account_name=os.environ['STORAGE_ACCOUNT'], account_key=os.environ['STORAGE_KEY'])
    #table_service.create_table(table_name=os.environ['REPOSITORY_TABLE']) #create if it doesn't exist
    results = table_service.query_entities(os.environ['REPOSITORY_TABLE'])
    for result in results:
        repo = json.loads(result['Repo'])
        repos.append(repo)

    return repos

def do_stage_one():
    repos = get_repos()
    chapter_repos = []
    gh = github.OWASPGitHub()
    for repo in repos:
        if 'www-chapter-' in repo['name']:
            chapter_repos.append(repo)

    if len(chapter_repos) > 0:
        logging.info("Building chapter json file")
        try:
            build_chapter_json(chapter_repos, gh)
        except Exception as err:
            logging.error(f"Exception building chapter json: {err}")
            raise err

def do_stage_two():
    repos = get_repos()
    project_repos = []
    gh = github.OWASPGitHub()
    for repo in repos:
        if 'www-project-' in repo['name']:
            project_repos.append(repo)

    if len(project_repos) > 0:
        logging.info("Building project json file")
        try:
            build_project_json(project_repos, gh)
        except Exception as err:
            logging.error(f"Exception building project json: {err}")
            raise err

def do_stage_three():
    lasterr = None
    repos = get_repos()
    committee_repos = []
    event_repos = []
    gh = github.OWASPGitHub()
    for repo in repos:
        if 'www-committee-' in repo['name']:
            committee_repos.append(repo)
        elif 'www-revent-' in repo['name']:
            event_repos.append(repo)            

    if len(committee_repos) > 0:
        logging.info('Building committees json file')
        try:
            build_committee_json(committee_repos, gh)
        except Exception as err:
            logging.error(f"Exception building committees json file: {err}")
            lasterr = err
    if len(event_repos) > 0:
        logging.info("Building event json file")
        try:
            build_event_json(event_repos, gh)
        except Exception as err:
            logging.error(f"Exception building event json: {err}")
            lasterr = err
    if lasterr:
        raise lasterr

def do_stage_four():
    repos = get_repos()
    gh = github.OWASPGitHub()
    
    logging.info('Building leaders json file')
    try:
        build_leaders_json(gh, repos)
    except Exception as err:
        logging.error(f"Exception updating leaders json file: {err}")
        raise err

def do_stage_five():
    repos = get_repos()
    gh = github.OWASPGitHub()

    logging.info('Updating community events')
    mu = meetup.OWASPMeetup()
    try:
        create_community_events(gh, mu, repos)
    except Exception as err:
        logging.error(f"Exception updating community events: {err}")
        raise err

def do_stage_six():
    gh = github.OWASPGitHub()

    logging.info('Updating Chapter Administration Team repositories')
    try:
        update_chapter_admin_team(gh)
    except Exception as err:
        logging.error(f"Exception updating Chapter Administration team: {err}")
        raise err

def do_stage_seven():
    repos = get_repos()
    gh = github.OWASPGitHub()
    logging.info('Updating inactive chapters')
    try:
        build_inactive_chapters_json(gh, repos)
    except Exception as err:
        logging.error(f"Exception updating inactive chapters: {err}")  
        raise err

def do_stage_eight():
    lasterr = None
    gh = github.OWASPGitHub()
    logging.info('Updating corp_members.yml sitedata from site.data')
    try:
        update_corp_members(gh)
    except Exception as err:
        logging.error(f"Exception updating corp_members.yml: {err}")
        lasterr = err

    logging.info('Building sitedata/events yml file')
    try:
        update_events_sitedata(gh)
    except Exception as err:
        logging.error(f"Exception building sitedata/events yml: {err}")
        lasterr = err

    if lasterr:
        raise lasterr

def main(name: str) -> str:
    if 'stage' not in name:
        logging.warn('Returning from func due to bad stage')
        return
        
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    logging.info('BuildSiteFiles function ran at %s with stage %s', utc_timestamp, name)
    
    if name == 'stage1':
        #do_stage_one()
        logging.info('Stage One now performed by Runbook')
    elif name == 'stage2':
        #do_stage_two()
        logging.info('Stage Two now performed by Runbook')
    elif name == 'stage3':
        #do_stage_three()
        logging.info('Stage Three now performed by Runbook')
    elif name == 'stage4':
        #do_stage_four()
        logging.info('Stage Four now performed by Runbook')
    elif name == 'stage5':
        #do_stage_five()
        logging.info('Stage Five now performed by Runbook')
    elif name == 'stage6':
        #do_stage_six()
        logging.info('Stage Six now performed by Runbook for Nightly Chapter Maintenance')
    elif name == 'stage7':
        logging.info('Stage Seven no longer required - using build')
    elif name == 'stage8':
        #do_stage_eight()
        logging.info('Stage Six now performed by Runbook')

    # Staff Projects no longer located on website (sarcasm:thanks for that :p )
    # logging.info("Building staff projects and milestones json files")
    # try:
    #     helperfuncs.build_staff_project_json(gh)
    # except Exception as err:
    #     logging.error(f"Exception building staff projects json: {err}")

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    logging.info(f"BuildSiteFiles finished at {utc_timestamp} with stage {name}")

    return name