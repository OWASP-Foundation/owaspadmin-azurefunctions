import requests
import json
import base64
from pathlib import Path
import os

class OWASPMeetup:
    meetup_api_url = "https://api.meetup.com"
    access_token = ''
    refresh_token = ''
    oauth_token = ''
    oauth_token_secret = ''

    def Login(self):
        login_url  = f"https://secure.meetup.com/oauth2/authorize?scope=basic+event_management+group_content_edit&client_id={os.environ['MU_CONSUMER_KEY']}&redirect_uri={os.environ['MU_REDIRECT_URI']}&response_type=anonymous_code"
        headers = {
            'Accept': 'application/json',
            'X-OAuth-Scopes': 'event_management, basic'
        }

        res = requests.post(login_url, headers=headers)
        result = False
        if '"code":' in res.text:
            try:
                json_res = json.loads(res.text)
                auth_code = json_res['code']
                login_url  = f"https://secure.meetup.com/oauth2/access?client_id={os.environ['MU_CONSUMER_KEY']}&client_secret={os.environ['MU_SECRET']}&code={auth_code}&redirect_uri={os.environ['MU_REDIRECT_URI']}&grant_type=anonymous_code"
                res = requests.post(login_url, headers=headers)
                json_res = json.loads(res.text)
                self.access_token = json_res['access_token']
                self.refresh_token = json_res['refresh_token']

                headers = {
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.access_token}'
                }
                login_url = f"https://api.meetup.com/sessions?email={os.environ['MU_USER_NAME']}&password={os.environ['MU_USER_PW']}"
                res = requests.post(login_url, headers=headers)
                json_res = json.loads(res.text)
                self.oauth_token = json_res['oauth_token']
                self.oauth_token_secret = json_res['oauth_token_secret']
                result = True

            except:
                result = False

        return result    

    def GetGroupEvents(self, groupname):
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.oauth_token}'
        }
        event_url = self.meetup_api_url + f'/{groupname}/events?desc=true&sign=true'
        res = requests.get(event_url, headers=headers)
        json_res = ''
        if res.ok:
            json_res = res.text
        return json_res