import requests
import json
import base64
from pathlib import Path
import os

class OWASPGitHub:
    apitoken = os.environ["GH_APITOKEN"]
    user = "harold.blankenship@owasp.com"
    gh_endpoint = "https://api.github.com/"
    org_fragment = "orgs/OWASP/repos"
    content_fragment = "repos/OWASP/:repo/contents/:path"
    pages_fragment = "repos/OWASP/:repo/pages"

    def CreateRepository(self, repoName):
        groupName = repoName
        repoName = self.FormatRepoName(repoName)
        data = { 
            "name": groupName, 
            "description": "a test chapter repo"
        }

        headers = {"Authorization": "token " + self.apitoken}
        r = requests.post(url = self.gh_endpoint + self.org_fragment, headers = headers, data=json.dumps(data))

        return r

    def InitializeRepositoryPages(self, repoName):
        groupName = repoName
        repoName = self.FormatRepoName(repoName)
        url = self.gh_endpoint + self.content_fragment
        url = url.replace(":repo", repoName)
        
        r = self.SendFile( url, "docs/index.html", "[GROUPNAME]", groupName)
        if self.TestResultCode(r.status_code):
            r = self.SendFile( url, "docs/_layouts/owasptest.html")
        
        if self.TestResultCode(r.status_code):
            r = self.SendFile( url, "docs/_includes/footer.html")

        if self.TestResultCode(r.status_code):
            r = self.SendFile( url, "docs/_includes/header.html")

        return r

    def SendFile(self, url, filename, replacetag = None, replacestr = None):
        url = url.replace(":path", filename)
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

    def EnablePages(self, repoName):
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.switcheroo-preview+json, application/vnd.github.mister-fantastic-preview+json, application/json"
        }
        repoName = self.FormatRepoName(repoName)
        url = self.gh_endpoint + self.pages_fragment
        url = url.replace(":repo", repoName)

        data = { "source" : { "branch" : "master", "path": "/docs"}}
        r = requests.post(url = url, headers=headers, data=json.dumps(data))

        return r

    def TestResultCode(self, rescode):
        if rescode == requests.codes.ok or rescode == requests.codes.created:
            return True

        return False

    def FormatRepoName(self, repoName):
        repoName = repoName.replace(" ", "-")
        return repoName

    def RebuildSite(self):
        headers = {"Authorization": "token " + self.apitoken,
            "Accept":"application/vnd.github.switcheroo-preview+json, application/vnd.github.mister-fantastic-preview+json, application/json"
        }
        repos = {"www--site-theme", "owasp.github.io", "www-project-zap"}
        for repo in repos:
            url = self.gh_endpoint + self.pages_fragment
            url = url.replace(":repo",repo)
            r = requests.post(url = url + "/builds", headers=headers)
            if not self.TestResultCode(r.status_code):
                break

        return r