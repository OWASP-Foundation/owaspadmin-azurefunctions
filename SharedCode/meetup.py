import requests
import json
import base64
from pathlib import Path
import os
import logging
import time
import random
from datetime import datetime, timedelta
import jwt
from jwt import algorithms
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class OWASPMeetup:
    meetup_api_url = "https://api.meetup.com"
    meetup_gql_url = "https://api.meetup.com/gql"
    access_token = ''
    refresh_token = ''
    oauth_token = ''
    oauth_token_secret = ''

    def HandleRateLimit(self):
        time.sleep(1 * random.randint(0, 3))

    def GetHeaders(self):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }

        return headers

    def Login(self):
        random.seed()
        now = datetime.utcnow()

        payload_dict = {
          "sub":os.environ['MU_USER_ID'],
          "iss":os.environ['MU_CONSUMER_KEY'],
          "aud":"api.meetup.com",
          "iat": now,
          "exp": (now + timedelta(hours=24)).timestamp()
        }
        jwtheaders = {"kid":os.environ['MU_KEY_ID'],
                       "alg":"RS256",
                       "typ":"JWT"}

        keystr = json.loads(os.environ["MU_RSA_KEY"])
        encoded_key = serialization.load_pem_private_key(keystr["key"].encode(), password=None)#keystr.encode()
        #pem = encoded_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
        encoded = jwt.encode(payload=payload_dict, key=encoded_key, algorithm='RS256', headers=jwtheaders)
        
        try:
            login_url = f"https://secure.meetup.com/oauth2/access"
            urldata = {
                 "grant_type" : "urn:ietf:params:oauth:grant-type:jwt-bearer",
                 "assertion" : encoded
             }
            res = requests.post(login_url, data=urldata, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept':'application/json'})
            
            json_res = json.loads(res.text)
            self.access_token = json_res['access_token']
            self.refresh_token = json_res['refresh_token']

            result = True

        except:
            result = False

        return result

    # def Login(self):
    #     login_url  = f"https://secure.meetup.com/oauth2/authorize?scope=basic+event_management+group_content_edit&client_id={os.environ['MU_CONSUMER_KEY']}&redirect_uri={os.environ['MU_REDIRECT_URI']}&response_type=anonymous_code"
    #     headers = {
    #         'Accept': 'application/json',
    #         'X-OAuth-Scopes': 'event_management, basic'
    #     }

    #     res = requests.post(login_url, headers=headers)
    #     result = False
    #     if '"code":' in res.text:
    #         try:
    #             json_res = json.loads(res.text)
    #             auth_code = json_res['code']
    #             login_url  = f"https://secure.meetup.com/oauth2/access?client_id={os.environ['MU_CONSUMER_KEY']}&client_secret={os.environ['MU_SECRET']}&code={auth_code}&redirect_uri={os.environ['MU_REDIRECT_URI']}&grant_type=anonymous_code"
    #             res = requests.post(login_url, headers=headers)
    #             json_res = json.loads(res.text)
    #             self.access_token = json_res['access_token']
    #             self.refresh_token = json_res['refresh_token']

    #             headers = {
    #                 'Accept': 'application/json',
    #                 'Authorization': f'Bearer {self.access_token}'
    #             }
    #             login_url = f"https://api.meetup.com/sessions?email={os.environ['MU_USER_NAME']}&password={os.environ['MU_USER_PW']}"
    #             res = requests.post(login_url, headers=headers)
    #             json_res = json.loads(res.text)
    #             self.oauth_token = json_res['oauth_token']
    #             self.oauth_token_secret = json_res['oauth_token_secret']
    #             result = True

    #         except:
    #             result = False

    #     return result    

    def GetGroupEvents(self, groupname, earliest = '', status = ''):
        headers = self.GetHeaders()
        
        id = self.GetGroupIdFromGroupname(groupname)
        if not status:
            status = "UPCOMING"
        datemax = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        datemin = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if earliest:
            datemin = earliest #here, we are assuming an ISO 8601 format date

        query = "query { proNetworkByUrlname(urlname: \"OWASP\") {"
        query += "eventsSearch(filter: { status: :STATUS groups: [ \":GROUPID\" ] "
        query += f"eventDateMin: \"{datemin}\" eventDateMax: \"{datemax}\""
        query += "  }, input: { first: 100 }) {"
        query += " count pageInfo { endCursor } edges { node { id title eventUrl dateTime timezone description }}}}}"
        query = query.replace(":GROUPID",id).replace(":STATUS", status.upper())
        query_data = {
            "query": query
        }
        
        
        json_res = ''
        tryagain = True
        count = 0
        maxcount = 5
        while(tryagain and count < maxcount):
            res = requests.post(self.meetup_gql_url, headers=headers, data=json.dumps(query_data))
            json_res = ''
            if res.ok:
                json_res = res.text
                tryagain = False
            elif 'throttled' in res.text:
                self.HandleRateLimit()
                count = count + 1
            else:
                logging.warn(f"GetGroupEvents failed with {res.text}")
                tryagain = False
                
        return json_res

    def GetGroupIdFromGroupname(self, groupname):
        headers = self.GetHeaders()
        querystr = "query {"
        querystr += " groupByUrlname(urlname: \"" + groupname + "\")"
        querystr += "{ id }"
        querystr += "}"

        query_data = {
            "query": querystr
        }
        
        res = requests.post(self.meetup_gql_url, headers=headers, data=json.dumps(query_data))
        id = ""
        if res.ok:
            jgroup = json.loads(res.text)
            if jgroup['data']['groupByUrlname']:
                id = jgroup['data']['groupByUrlname']['id']
                
        return id
