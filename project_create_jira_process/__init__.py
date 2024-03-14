import logging
import os
import requests
import azure.functions as func
import json
import logging
import base64
from jira import JIRA
from datetime import timedelta, datetime
from ..SharedCode.helperfuncs import MemberData
from ..SharedCode.github import OWASPGitHub
from ..SharedCode.copper import OWASPCopper
from ..SharedCode.googleapi import OWASPGoogle

def main(msg: func.QueueMessage, context: func.Context) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    
    post_dict = json.loads(msg.get_body().decode("utf-8"))

    jira_id = post_dict.get('jira_id')
    command = post_dict.get('command')
    response_url = post_dict.get('response_url')

    if command == '/project-create-jira':
        project_create(jira_id, context.function_directory, response_url)
    else:
        logging.error("Unknown command. Received: %s", command)

def get_project_type(project_type):
    ptype = "unknown"
    if "Documentation" in project_type:
        ptype = "documentation"
    elif "Code" in project_type:
        ptype = "code"

    return ptype

def add_to_project_levels(gh :OWASPGitHub, name, reponame):
    resString = "Added to project levels"
    r = gh.GetFile("owasp.github.io", "_data/project_levels.json")
    if r.ok:
        doc = json.loads(r.text)
        sha = doc['sha']
        content = base64.b64decode(doc['content']).decode(encoding='utf-8')
        plevels = json.loads(content)
        # assumption is that project does not exist in file as these are new projects
        project = {
            "name": name,
            "repo": reponame,
            "level": 2 # incubator
        }
        plevels.append(project)
        

        newcontents = json.dumps(plevels, indent=4)
        r = gh.UpdateFile('owasp.github.io', '_data/project_levels.json', newcontents, sha)
        if not r.ok:
            resString = "Failed to update project levels"
            logging.warn("Failed to update project levels")
    else:
        resString = "Failed to add to project levels"
        logging.warn("Not added to project levels file")
    return resString

def project_create(jira_id, function_directory, response_url):
    jira = JIRA(server="https://owasporg.atlassian.net", basic_auth=(os.environ["JIRA_USER"], os.environ["JIRA_API_TOKEN"]))
    issue = jira.issue(jira_id)

    try:
        jira.transition_issue(issue, "In Progress")
    except:
        try:
            jira.transition_issue(issue, "Back to in progress")
        except:
            pass

    nameMap = {field['name']:field['id'] for field in jira.fields()}
    resString = ""
    project_name = getattr(issue.fields, nameMap['Project Name'], None)
    project_name = project_name.replace('OWASP','').replace('Owasp','').replace('owasp','').strip()
    
    project_type = getattr(issue.fields, nameMap['Project Type'], None)
    if project_type:
        project_type = project_type.value
    #project_class = getattr(issue.fields, nameMap['Project Classification'], None)
    license = getattr(issue.fields, nameMap['Open Source License'],'Other')
    if license and license != 'Other':
        license = license.value

    leader_emails = getattr(issue.fields, nameMap['Leader Emails'], None)
    if leader_emails == None:
        leader_emails = getattr(issue.fields, nameMap['Payee Email'], None)
    
    leader_names = getattr(issue.fields, nameMap['Leader Names'], None)
    if leader_names == None:
        leader_names = getattr(issue.fields, nameMap['Payee Name'], None)

    leader_gh = getattr(issue.fields, nameMap['Leader Github Usernames'], None)
    if leader_gh == None:
        leader_gh = getattr(issue.fields, nameMap['Expense'], None)

    if leader_names == None or leader_emails == None or leader_gh == None:
        resString = "Failed due to missing leader information."

    if not 'Failed' in resString:
        project_deliverable = getattr(issue.fields, nameMap['Generic Text Area 1'], None) # summary
        project_description = getattr(issue.fields, nameMap['Generic Text Area 2'], None) # description
        project_roadmap = getattr(issue.fields, nameMap['Generic Text Area 3'], None) # roadmap
        project_comments = getattr(issue.fields, nameMap['Generic Text Area 4'], None) # usually a license not mentioned
            
        leaders = leader_names.splitlines()
        emails = leader_emails.splitlines()
        gitusers = leader_gh.splitlines()
        emaillinks = []
        if len(leaders) == len(emails):
            count = 0
            useemails = CreateOWASPEmails(leaders, emails)
            for leader in leaders:
                email = useemails[count]
                count = count + 1
                logging.info("Adding project leader...")

                emaillinks.append(f'[{leader}](mailto:{email})')
                
            logging.info("Creating github repository")
            proj_type = get_project_type(project_type)
            resString = CreateGithubStructure(project_name, function_directory, proj_type, emaillinks, gitusers, project_description, project_roadmap)
            # do copper integration here
            if not 'Failed' in resString:
                resString = CreateCopperObjects(project_name, leaders, emails, gitusers, proj_type, license)
            
        else:
            resString = "Failed due to non matching leader names with emails"
    
    gh = OWASPGitHub()
    reponame = gh.FormatRepoName(project_name, gh.GH_REPOTYPE_PROJECT)
    if not 'Failed' in resString:                
        # also need to add to project_levels.json file...        
        resString = add_to_project_levels(gh, project_name, reponame)

    if not 'Failed' in resString:
        comment = "Please find your OWASP web page for the project at [link]. You can edit your website page by going to 'Edit on GitHub' at the bottom of the page.\n"
        comment = comment.replace("[link]", f"https://owasp.org/{reponame}")
        comment += "It is highly desirable that any source reside under a project repo (outside the above webpage repo) within the http://github.com/OWASP  organization. If it is not an undue burden, we would appreciate that any source outside the OWASP org get moved or mirrored within the OWASP org.\n\n"
        comment += "Next Steps:\n\n"
        comment += "* Update the web pages for your project\n"
        comment += "* Look for other people to help you lead and contribute to your project.Yay for you! Project created."
        jira.transition_issue(issue, "Resolve this issue", resolution={'id': '10000'}, comment=comment)

    resp = {
        "blocks": []
    }
    fields = []
    if "Failed" not in resString:
        fields.append({
                "type": "mrkdwn",
                "text": project_name + " created.\n"
            })
    else:
        fields.append({"type": "mrkdwn",
                       "text": "Failed to create " + project_name + ". Reason: " + resString
                       })
    resp['blocks'].append({
        "type": "section",
        "fields": fields
        })
    
    logging.info(resp)
    requests.post(response_url, json=resp)

def CreateOWASPEmails(leaders :[str], emails :[str]):
    ggl = OWASPGoogle()
    cp = OWASPCopper()
    use_emails = []
    count = 0

    for leader in leaders:
        email = emails[count]
        if 'owasp.org' not in email.lower():
            person = cp.FindPersonByEmailObj(email)
            owemail = cp.GetOWASPEmailForPerson(person)
            if owemail != '':
                use_emails.append(owemail)
            else:
                #create an owasp email and use that....
                names = leader.split(' ')
                first = names[0].strip()
                last = ""
                if len(names) > 1: ## this should be the case but...you never know
                    for name in names[1:]:
                        last += name
                owemail = ggl.CreateEmailAddress(email, first, last, True)
                if 'already exists' in owemail:    
                    preferred_email = first + "." + last + "@owasp.org"
                    possible_emails = ggl.GetPossibleEmailAddresses(preferred_email)
                    for pemail in possible_emails:
                        owemail = ggl.CreateSpecificEmailAddress(email, first, last, pemail)
                        if 'already exists' not in owemail:
                            owemail = pemail
                            break
                    use_emails.append(owemail)
                else:
                    owemail = first + "." + last + "@owasp.org"
                    use_emails.append(owemail)
        else:
            use_emails.append(email)

    return use_emails

def CreateCopperObjects(project_name, leaders, emails, gitusers, type, license):
    resString = 'Project created.'
    cp = OWASPCopper()
    gh = OWASPGitHub()
    repo = gh.FormatRepoName(project_name, gh.GH_REPOTYPE_PROJECT)
    project_name = "Project - OWASP " + project_name
    project_type = OWASPCopper.cp_project_project_type_option_other
    if type == "documentation":
        project_type = OWASPCopper.cp_project_project_type_option_documentation
    elif type == "code":
        project_type = OWASPCopper.cp_project_project_type_option_code

    project_options = {
        "level": OWASPCopper.cp_project_project_level_option_incubator,
        "type": project_type,
        "license": license
    }

    if cp.CreateProject(project_name, leaders, emails, gitusers, OWASPCopper.cp_project_type_option_project, OWASPCopper.cp_project_chapter_status_option_active, repo = repo, project_options=project_options) == '':
        resString = "Failed to create Copper objects"

    return resString

def CreateGithubStructure(project_name, func_dir, proj_type, emaillinks, gitusers, description, roadmap):
    gh = OWASPGitHub()
    r = gh.CreateRepository(project_name, gh.GH_REPOTYPE_PROJECT)
    resString = "Project created."
    if not gh.TestResultCode(r.status_code):
        resString = f"Failed to create repository for {project_name}."
        logging.error(resString + " : " + r.text)
    

    if resString.find("Failed") < 0:
        r = gh.InitializeRepositoryPages(project_name, gh.GH_REPOTYPE_PROJECT, basedir = func_dir, proj_type=proj_type, description=description, roadmap=roadmap)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to send initial files for {project_name}."
            logging.error(resString + " : " + r.text)

    repoName = gh.FormatRepoName(project_name, gh.GH_REPOTYPE_PROJECT)

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
        r = gh.EnablePages(project_name, gh.GH_REPOTYPE_PROJECT)
        if not gh.TestResultCode(r.status_code):
            resString = f"Failed to enable pages for {project_name}."
            logging.error(resString + " : " + r.text)

    return resString


