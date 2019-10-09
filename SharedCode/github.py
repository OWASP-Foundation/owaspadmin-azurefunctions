import requests
import json
import base64
from pathlib import Path
import os
import logging

class OWASPGitHub:
    apitoken = os.environ["GH_APITOKEN"]
    user = "harold.blankenship@owasp.com"
    gh_endpoint = "https://api.github.com/"
    org_fragment = "orgs/OWASP/repos"
    content_fragment = "repos/OWASP/:repo/contents/:path"
    pages_fragment = "repos/OWASP/:repo/pages"

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

    def InitializeRepositoryPages(self, repoName, rtype):
        groupName = repoName
        repoName = self.FormatRepoName(repoName, rtype)
        url = self.gh_endpoint + self.content_fragment
        url = url.replace(":repo", repoName)
        # change to use files.json....
        sfile = open("files.json")
        filestosend = json.load(sfile)
        for f in filestosend["files"]:
            r = self.SendFile( url, f['path'], "[GROUPNAME]", groupName)
            if not self.TestResultCode(r.status_code):
                break

        return r

    def SendFile(self, url, filename, replacetag = None, replacestr = None):
        pathname = filename.replace("docs/", "")
        url = url.replace(":path", pathname)
        sfile = open(filename)
        filecstr = sfile.read()
        if replacetag and replacestr:
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
        else:
            resName = "www-chapter-"
    
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