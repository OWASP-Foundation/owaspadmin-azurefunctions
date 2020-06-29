import logging

import azure.functions as func
from ..SharedCode import github
from googleapiclient.discovery import build

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('get-repo-file triggered')
    
    origin = req.headers.get("Origin")
    if not origin:
        origin = "http://localhost" 
        
    if req.method == "OPTIONS": # just return the headers
        response = func.HttpResponse(status_code=200)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response
    if req.params.get('test') == 'true':
        return func.HttpResponse(
             "A most excellent test.",
             status_code=200
        )  

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
        response = func.HttpResponse(status_code=200, body=r.text)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response
    else:
        return func.HttpResponse(
             "File request failed for repo",
             status_code=400
        )
