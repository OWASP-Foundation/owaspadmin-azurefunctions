import requests
import json
import base64
from pathlib import Path
import os
import logging
import datetime

class OWASPGitHub:
    apitoken = os.environ["GH_APITOKEN"]
    user = "harold.blankenship@owasp.com"
    gh_endpoint = "https://api.github.com/"
    org_fragment = "orgs/OWASP/repos"
    content_fragment = "repos/OWASP/:repo/contents/:path"
    pages_fragment = "repos/OWASP/:repo/pages"
    team_addrepo_fragment = "teams/:team_id/repos/OWASP/:repo"
    team_getbyname_fragment = "orgs/OWASP/teams/:team_slug"
    collab_fragment = "repos/OWASP/:repo/collaborators/:username"

    PERM_TYPE_PULL = "pull"
    PERM_TYPE_PUSH = "push"
    PERM_TYPE_ADMIN = "admin"
    PERM_TYPE_MAINTAIN = "maintain"
    PERM_TYPE_TRIAGE = "triage"

    GH_REPOTYPE_PROJECT = 0
    GH_REPOTYPE_CHAPTER = 1
    GH_REPOTYPE_COMMITTEE = 2

    def CreateRepository(self, repoName, rtype):
        repoName = self.FormatRepoName(repoName, rtype)
        description = "OWASP Foundation Web Respository"
        data = { 
            "name": repoName, 
            "description": description
        }

        headers = {"Authorization": "token " + self.apitoken}
        r = requests.post(url = self.gh_endpoint + self.org_fragment, headers = headers, data=json.dumps(data))

        return r

    def InitializeRepositoryPages(self, repoName, rtype, basedir = "", region="", proj_type = ""):
        if basedir and not basedir.endswith('/'):
            basedir = basedir + '/'

        groupName = repoName
        repoName = self.FormatRepoName(repoName, rtype)
        url = self.gh_endpoint + self.content_fragment
        url = url.replace(":repo", repoName)
        # change to use files.json....
        sfile = open(basedir + "files.json")
        filestosend = json.load(sfile)
        for f in filestosend["files"]:
            fpath = basedir + f['path']
            
            r = self.SendFile( url, fpath, ["[GROUPNAME]", "[:REGION]", "[:PROJTYPE]"], [groupName, region, proj_type])
            if not self.TestResultCode(r.status_code):
                break

        return r

    def GetFile(self, repo, filepath):
        url = self.gh_endpoint + self.content_fragment
        url = url.replace(":repo", repo)
        url = url.replace(":path", filepath)
        
        #bytestosend = base64.b64encode(filecstr.encode())   
        headers = {"Authorization": "token " + self.apitoken}
        r = requests.get(url = url, headers=headers)
        return r

    def SendFile(self, url, filename, replacetags = None, replacestrs = None):
        pathname = filename[filename.find("docs/") + 5:]
        if pathname == "gitignore":
            pathname = "." + pathname
            
        url = url.replace(":path", pathname)
        sfile = open(filename)
        filecstr = sfile.read()
    
        if replacetags and replacestrs and len(replacetags) > 0 and len(replacetags) == len(replacestrs):
            for idx, replacetag in enumerate(replacetags):
                replacestr = replacestrs[idx] # this is liquid, not python...
                filecstr = filecstr.replace(replacetag, replacestr)

        bytestosend = base64.b64encode(filecstr.encode())   
        committer = {
            "name" : "OWASP Foundation",
            "email" : "owasp.foundation@owasp.org"
        }
        data = {
            "message" : "initialize repo",
            "committer" : committer,
            "content" : bytestosend.decode()
        }
        headers = {"Authorization": "token " + self.apitoken}
        r = requests.put(url = url, headers=headers, data=json.dumps(data))
        return r

    def EnablePages(self, repoName, rtype):
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.switcheroo-preview+json, application/vnd.github.mister-fantastic-preview+json, application/json"
        }
        repoName = self.FormatRepoName(repoName, rtype)
        url = self.gh_endpoint + self.pages_fragment
        url = url.replace(":repo", repoName)

        data = { "source" : { "branch" : "master" }}
        r = requests.post(url = url, headers=headers, data=json.dumps(data))

        return r

    def TestResultCode(self, rescode):
        if rescode == requests.codes.ok or rescode == requests.codes.created:
            return True

        return False

    def FormatRepoName(self, repoName, rtype):
        
        resName = ""
        if rtype == 0:
            resName = "www-project-"
        elif rtype == 1:
            resName = "www-chapter-"
        else:
            resName = "www-committee-"
    
        return resName + repoName.replace(" ", "-").lower()


    def RebuildSite(self):
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.switcheroo-preview+json, application/vnd.github.mister-fantastic-preview+json, application/json, application/vnd.github.baptiste-preview+json"
        }
        
        done = False
        pageno = 1
        pageend = -1
        
        while not done:
            pagestr = "?page=%d" % pageno
            url = self.gh_endpoint + self.org_fragment + pagestr
            r = requests.get(url=url, headers = headers)
            
            if self.TestResultCode(r.status_code):
                repos = json.loads(r.text)
                if pageend == -1:
                    endlink = r.links["last"]["url"]
                    pageend = int(endlink[endlink.find("?page=") + 6:])
                
                if pageno == pageend:
                    done = True
                
                pageno = pageno + 1
                #repos = {"www--site-theme", "owasp.github.io", "www-project-zap"}
                for repo in repos:
                    repoName = repo["name"].lower()
                    istemplate = repo["is_template"]
                    if not istemplate and (repoName.startswith("www-project") or repoName.startswith("www-chapter") or repoName.startswith("www--") or repoName.startswith("owasp.github")):
                        logging.info("rebuilding " + repoName + "\n")
                        url = self.gh_endpoint + self.pages_fragment
                        url = url.replace(":repo",repoName)
                        r = requests.post(url = url + "/builds", headers=headers)
                        if not self.TestResultCode(r.status_code):
                            logging.warn(repoName + " not rebuilt: " + r.text)

        return r

    def UpdateFile(self, repo, filepath, contents, sha):
        url = self.gh_endpoint + self.content_fragment
        url = url.replace(":repo", repo)
        url = url.replace(":path", filepath)

        bytestosend = base64.b64encode(contents.encode())   
        committer = {
            "name" : "OWASP Foundation",
            "email" : "owasp.foundation@owasp.org"
        }
        data = {
            "message" : "remote update file",
            "committer" : committer,
            "content" : bytestosend.decode(),
            "sha" : sha
        }
        headers = {"Authorization": "token " + self.apitoken}
        r = requests.put(url = url, headers=headers, data=json.dumps(data))
        return r

    def GetPages(self, repoName):
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.switcheroo-preview+json, application/vnd.github.mister-fantastic-preview+json, application/json, application/vnd.github.baptiste-preview+json"
        }
        result = ''
        url = self.gh_endpoint + self.pages_fragment
        url = url.replace(':repo', repoName)

        r = requests.get(url=url, headers = headers)
        if r.ok:
            result = json.loads(r.text)
        
        return result

    def GetInactiveRepositories(self, matching=""):
       return self.GetPublicRepositories(matching=matching, inactive=True)

    def GetPublicRepositories(self, matching="", inactive=False):
        headers = {"Authorization": "token " + self.apitoken, "X-PrettyPrint":"1",
            "Accept":"application/vnd.github.switcheroo-preview+json, application/vnd.github.mister-fantastic-preview+json, application/json, application/vnd.github.baptiste-preview+json"
        }
        
        done = False
        pageno = 1
        pageend = -1
        
        results = []
        while not done:
            pagestr = "?page=%d" % pageno
            url = self.gh_endpoint + self.org_fragment + pagestr
            r = requests.get(url=url, headers = headers)
            
            if self.TestResultCode(r.status_code):
                repos = json.loads(r.text)
                if pageend == -1:
                    endlink = r.links['last']['url']
                    pageend = int(endlink[endlink.find('?page=') + 6:])
                
                if pageno == pageend:
                    done = True
                
                pageno = pageno + 1
                
                for repo in repos:
                    repoName = repo['name'].lower()
                    istemplate = repo['is_template']
                    haspages = repo['has_pages'] #false for Iran...maybe was never activated?
                        
                    if not matching or matching in repoName:
                        if not istemplate:
                            pages = None
                            if haspages:
                                pages = self.GetPages(repoName)
                            if (not pages or pages['status'] == None) and not inactive:
                                continue
                            elif (pages and pages['status'] != None) and inactive:
                                continue
                        else:
                            continue
                        
                        addrepo = {}
                        addrepo['name'] = repoName
                        addrepo['url'] = f"https://owasp.org/{ repoName }/"
                    
                        cdate = datetime.datetime.strptime(repo['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                        udate = datetime.datetime.strptime(repo['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
                        addrepo['created'] = cdate.strftime('%c')
                        addrepo['updated'] = udate.strftime('%c')
                        r = self.GetFile(repoName, 'index.md')
                        if self.TestResultCode(r.status_code):
                            doc = json.loads(r.text)
                            content = base64.b64decode(doc['content']).decode()
                            ndx = content.find('title:')
                            eol = content.find('\n', ndx + 7)
                            if ndx >= 0:
                                title = content[ndx + 7:eol]
                                addrepo['title'] = title.strip()
                            else:
                                addrepo['title'] = repoName
                                
                            ndx = content.find('level:') + 6
                            eol = content.find("\n", ndx)
                            not_updated = (content.find("This is an example of a Project") >= 0)
                            if ndx < 0 or not_updated:
                                level = "-1"
                            else:
                                level = content[ndx:eol]
                            addrepo['level'] = level.strip() 
                            ndx = content.find('type:') + 5
                            eol = content.find("\n", ndx)
                            gtype = content[ndx:eol]
                            addrepo['type'] = gtype.strip()
                            ndx = content.find('region:') + 7
                            
                            if not_updated:
                                gtype = 'Needs Website Update'
                            elif ndx > 6: # -1 + 7
                                eol = content.find("\n", ndx)
                                gtype = content[ndx:eol]
                            else: 
                                gtype = 'Unknown'
                                
                            addrepo['region'] = gtype.strip()

                            ndx = content.find('pitch:') + 6
                            if ndx > 5: # -1 + 6
                                eol = content.find('\n', ndx)
                                gtype = content[ndx:eol]
                            else:
                                gtype = 'More info soon...' 
                            addrepo['pitch'] = gtype.strip()

                            results.append(addrepo)



        return results

    def GetFilesMatching(self, repo, path, matching=''):
        rfiles = []
        url = self.gh_endpoint + self.content_fragment
        url = url.replace(":repo", repo)
        url = url.replace(":path", path)   
        headers = {"Authorization": "token " + self.apitoken}
        r = requests.get(url = url, headers=headers)
        if self.TestResultCode(r.status_code):
            contents = json.loads(r.text)
            for item in contents:
                if item['type'] == 'file':
                    if matching and item['name'].find(matching) > -1:
                        rfiles.append(item['name'])
                    elif not matching:
                        rfiles.append(item['name'])
    
        return r, rfiles

    def GetTeamId(self, team_name):
        getTeamUrl = self.team_getbyname_fragment.replace(':team_slug', team_name)
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.hellcat-preview+json, application/vnd.github.inertia-preview+json"
        }
        url = self.gh_endpoint + getTeamUrl
        r = requests.get(url = url, headers=headers)
        team_id = None
        if r.ok:
            jsonTeam = json.loads(r.text)
            team_id = jsonTeam['id']

        return team_id

    def AddRepoToTeam(self, team_id, repo):
        repofrag = self.team_addrepo_fragment.replace(':team_id', team_id)
        repofrag = repofrag.replace(':repo', repo)
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.hellcat-preview+json, application/vnd.github.inertia-preview+json"
        }

        url = self.gh_endpoint + repofrag

        data = { "permission" : self.PERM_TYPE_ADMIN}
        jsonData = json.dumps(data)
        r = requests.put(url = url, headers=headers, data=jsonData)

        return r

    def AddPersonToRepo(self, person, repo):
        collabfrag = self.collab_fragment.replace(':repo', repo)
        collabfrag = collabfrag.replace(':username', person)
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.hellcat-preview+json, application/vnd.github.inertia-preview+json"
        }

        url = self.gh_endpoint + collabfrag

        data = { "permission" : self.PERM_TYPE_ADMIN}
        jsonData = json.dumps(data)
        r = requests.put(url = url, headers=headers, data=jsonData)

        return r