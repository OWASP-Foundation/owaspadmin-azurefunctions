import json

import requests
import os
import logging
import time
import hmac
import hashlib

class OWASPGlueup:
    # The base URL for the GlueUp API
    gu_base_url = os.environ.get('GLUEUP_ENDPOINT', 'https://api-services.glueup.com/v2/')

    # init method to initialize the class with the necessary parameters
    def __init__(self):
        self.account = os.environ.get('GLUEUP_ACCOUNT', '')
        self.tenant = os.environ.get('GLUEUP_TENANT', '')
        self.orgid = os.environ.get('GLUEUP_ORGID', '')
        self.api_version = os.environ.get('GLUEUP_API_VERSION', 'v1')
        self.base_url = self.gu_base_url
                
        self.logger = logging
    
    def getHeaders(self, method :str, token :str = ''):
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        ts = int(time.time()) * 1000
        hash = method.upper() + self.account + self.api_version + str(ts)
        d    = hmac.new(os.environ.get('GLUEUP_PRIVATE_KEY', '').encode(), hash.encode(), hashlib.sha256)
        a    = 'd=' + d.hexdigest() + ';v=' + self.api_version + ';k=' + self.account + ';ts=' + str(ts)

        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'
        headers['tenantId'] = self.tenant
        headers['a'] = a

        if ( token != '' ):
            headers['token'] = token

        return headers

    def getMembers(self, token :str = ''):
        url = self.base_url + 'membershipDirectory/individualMemberships'
        headers = self.getHeaders('POST', token)
        params = {
            "projection": [],
            "filter": [               
                # Removing the filters for membershipType.id and membershipType.status.code to get all members regardless of type or status as per Glueup (though the numbers are still wrong)
                # {
                #     "projection": "membershipType.id",
                #     "operator": "eq",
                #     "values": ["28599","28688","28686","29743","29744","29843","28741","29134","28542","34087"],
                # },
                # {
                #     "projection": "membershipType.status.code",
                #     "operator": "eq",
                #     "values": ["Active","GracePeriod"],
                # },
            ],
            "search": {                
            },
            "order": {
                "name": "asc",
            },
            "offset": 0,
            "limit": 7000,
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(params))
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to get members: {response.status_code} - {response.text}")
            return None
        

    def getEvents(self, token :str = ''):
        url = self.base_url + 'event/list'
        headers = self.getHeaders('POST', token)
        params = {}

        # Projections
        # List of properties requested.
        params["projection"] = [
            "id",
            "language.code",
            "defaultLanguage.code",
            "title",
            "template",
            "startDateTime",
            "endDateTime",
            "venueInfo",
            "eventTag",
            "workingGroup",
            "eventType.code",
            "eventType.name",
        ]

        # Pagination
        # Provide the offset and limit in order to retrieve a limited amount of items.
        params["offset"] = 0
        params["limit"] = 5

        # Order
        # Let you order the requested list using the properties available.
        # You can add more properties to order with more criteria.
        params["order"] = {"startDateTime": "asc"}

        # Filter
        # Let you filter the requested list using the properties available.
        # For each filter, you need to specify a valid projection, the wanted operator and the values as an array.
        params["filter"] = [
            {
                "projection": "openToPublic",
                "operator": "eq",
                "values": [True],
            },
            {
                "projection": "published",
                "operator": "eq",
                "values": [True],
            },
        ]
        response = requests.post(url, headers=headers, data=json.dumps(params))
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to get events: {response.status_code} - {response.text}")
            return None