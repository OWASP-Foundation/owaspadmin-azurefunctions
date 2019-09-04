import logging
import os
import azure.functions as func
from ..SharedCode import github
from ..SharedCode import spotchk

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    body = req.get_body()
    strbody = body.decode("utf-8")
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )

    names = dict(x.split('=') for x in strbody.split('&'))
    
    if not spotchk.spotchk().validate_query(names):
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )

    # no parameters, just a simple rebuild-site
    gh = github.OWASPGitHub()
    r = gh.RebuildSite()
    resString = r.text
    if resString.find("queued"):
        resString = "Build queued"
    return func.HttpResponse(
            resString,
            status_code=200
    )
