import logging
import os
import azure.functions as func
import requests
import json
from ..SharedCode import salesforce
from ..SharedCode import spotchk
from urllib.parse import unquote_plus
import pathlib


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('chapter-create request')
    
    # sf = salesforce.OWASPSalesforce()
    # sf.Login()
    # r = sf.GetChapter('Colombo')
    # cg_json = json.loads(r.text)

    body = req.get_body()
    
    # validate the call...
    strbody = unquote_plus(body.decode("utf-8"))
    if len(strbody) < 10 or strbody.find('&') < 0 or strbody.find('=') < 0:
        return func.HttpResponse(
            'Call not valid (100)',
            status_code = 200
        )
    names = dict(x.split('=') for x in strbody.split('&'))
    
    if not spotchk.spotchk().validate_query2(names):
        return func.HttpResponse(
            'Call not valid (101)',
            status_code = 200
        )
    # validation complete...let's do something...
    
    with open(pathlib.Path(__file__).parent / 'create_ch_dialog.json') as dfile:
        strdialog = dfile.read()
    
    strdata = "{ 'trigger_id': '" + names['trigger_id'] + "'," + "'view': '" + strdialog + "'}"

    urldialog = "https://slack.com/api/views.open"
    headers = {'content-type':'application/json; charset=utf-8', 'Authorization':f'Bearer {os.environ["SL_ACCESS_TOKEN_GENERAL"]}' }

    # respond to caller...
    r = requests.post(url = urldialog, headers=headers, data=strdata)
    json_response = json.loads(r.text)
    if json_response["ok"] == True:
        return func.HttpResponse()
    else:
        return func.HttpResponse(r.text)
