import datetime
import logging
import json
import re
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import helperfuncs
from ..SharedCode import meetup

import base64
##############################################################
# THIS FILE IS DEPRECATED AND SHOULD NO LONGER BE IN SERVICE #
##############################################################

def parse_leaderline(line):
    ename = line.find(']')
    name = line[line.find('[') + 1:line.find(']')]
    email = line[line.find('(', ename) + 1:line.find(')', ename)]
    return name, email

def add_to_leaders(repo, content, all_leaders, stype):
    lines = content.split('\n')
    max_leaders = 5
    leader_count = 0
    in_leaders = False
    for line in lines:
        testline = line.lower()
        if in_leaders and leader_count > 0 and not testline.startswith('*'):
            break
        
        if(testline.startswith('###') and 'leader' not in testline):
            break
        elif testline.startswith('###') and 'leader' in testline:
            in_leaders = True
            continue

        fstr = line.find('[')
        if((line.startswith('-') or line.startswith('*')) and fstr > -1 and fstr < 4):
            name, email = parse_leaderline(line)
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
    r = gh.UpdateFile('owasp.github.io', '_data/leaders.json', json.dumps(all_leaders, ensure_ascii=False, indent = 4), sha)
    if r.ok:
        logging.info('Update leaders json succeeded')
    else:
        logging.error(f'Update leaders json failed: {r.status}')

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
    
    if len(mue) <= 0 or 'errors' in mue:
        return events
    
    group = repo.replace('www-chapter-','').replace('www-project-','').replace('www-committee-','').replace('www-revent-','').replace('-', ' ')
    group = " ".join(w.capitalize() for w in group.split())
                
    for mevent in mue:
        event = {}
        today = datetime.datetime.today()
        eventdate = datetime.datetime.strptime(mevent['local_date'], '%Y-%m-%d')
        tdelta = eventdate - today
        if tdelta.days >= -1 and tdelta.days <= 30:
            event['group'] = group
            event['repo'] = repo
            event['name'] = mevent['name']
            event['date'] = mevent['local_date']
            event['time'] = mevent['local_time']
            event['link'] = mevent['link']
            event['timezone'] = mevent['group']['timezone']
            if 'description' in mevent:
                event['description'] = deEmojify(mevent['description'])
            else:
                event['description'] = ''
                
            events.append(event)

    return events

def create_community_events(gh, mu, repos):
    #repos = gh.GetPublicRepositories('www-')
    
    events = []
    edate = datetime.datetime.today() + datetime.timedelta(-30)
    earliest = edate.strftime('%Y-%m-')+"01T00:00:00.000"

    for repo in repos:
        rname = repo['name']
        if 'www-chapter' not in rname and 'www-project' not in rname and 'www-committee' not in rname and 'www-revent' not in rname:
            continue

        if 'meetup-group' in repo and repo['meetup-group']:
            if mu.Login():
                mstr = mu.GetGroupEvents(repo['meetup-group'], earliest)
                if mstr:
                    muej = json.loads(mstr)
                    add_to_events(muej, events, rname)
                

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

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    gh = github.OWASPGitHub()
    logging.info('BuildStatisWebsiteFilesTwo ran at %s but will do nothing for now.', utc_timestamp)
    return
    
    #call get repos like this once because leaders and community events both use it
    # repos = gh.GetPublicRepositories('www-')
    # logging.info('Building leaders json file')
    # try:
    #     build_leaders_json(gh, repos)
    # except Exception as err:
    #     logging.error(f"Exception updating leaders json file: {err}")
    
    # logging.info('Updating community events')
    # mu = meetup.OWASPMeetup()
    # try:
    #     create_community_events(gh, mu, repos)
    # except Exception as err:
    #     logging.error(f"Exception updating community events: {err}")

    # logging.info('Updating inactive chapters')
    # try:
    #     build_inactive_chapters_json(gh)
    # except Exception as err:
    #     logging.error(f"Exception updating inactive chapters: {err}")

    # logging.info('BuildStaticWebsiteFilesTwo timer trigger function ran at %s', utc_timestamp)