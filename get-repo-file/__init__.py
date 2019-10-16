import logging

import azure.functions as func
from ..SharedCode import github

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('get-repo-file triggered')
    
    fpath = req.params.get('filepath')
    repo = req.params.get('repo')
    if not fpath or repo:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            fpath = req_body.get('filepath')
            repo = req_body.get('repo')

    if fpath and repo:
        gh = github.OWASPGitHub()
        r = gh.GetFile(repo, fpath)
        
        return func.HttpResponse(r.text)
    else:
        return func.HttpResponse(
             "File request failed for repo",
             status_code=400
        )
