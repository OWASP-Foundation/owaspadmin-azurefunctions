import logging
import os
import azure.functions as func
from ..SharedCode import github

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    salt_secret = os.environ['SL_TEAM']
    salt_provider = os.environ['SL_RURL']
    salt_bind = os.environ['SL_COMM']

    body = req.get_body()
    strbody = body.decode("utf-8")
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )

    names = dict(x.split('=') for x in strbody.split('&'))
    testsec = names[os.environ['P_SECRET']]
    testprov = names[os.environ['P_PROVIDER']]
    testcomm = names[os.environ['P_COMM']]

    # minor annoyance for callers not from official sources
    if testsec != salt_secret or testprov.find(salt_provider) < 0 or testcomm != salt_bind:
        return func.HttpResponse(
            'Rebuild site delayed 200ms',
            status_code = 200
        )

    # no parameters, just a simple rebuild-site
    gh = github.OWASPGitHub()
    r = gh.RebuildSite()

    return func.HttpResponse(
            r.text,
            status_code=200
    )
