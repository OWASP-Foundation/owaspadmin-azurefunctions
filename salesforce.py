import requests
import json
import base64
from pathlib import Path
import os
import logging

class OWASPSalesforce:
    sf_consumer_key = os.environ["SF_CONSUMER_KEY"]
    sf_consumer_secret = os.environ["SF_CONSUMER_SECRET"]
    sf_user_name = os.environ["SF_USER_NAME"]
    sf_user_pw = os.environ["SF_USER_PW"]
    sf_user_security_token = os.environ["SF_USER_SECURITY_TOKEN"]

    sf_login_url = "https://login.salesforce.com/services/oauth2/token"
    sf_instance_url = "https://na131.salesforce.com"
    sf_api_url = "/services/data/v46.0/"
    sf_token_id = ""
    sf_query_url = sf_instance_url + sf_api_url + "query"

    def Login(self):
        data = dict(grant_type='password',
                    client_id=self.sf_consumer_key,
                    client_secret=self.sf_consumer_secret,
                    username=self.sf_user_name,
                    password=self.sf_user_pw + self.sf_user_security_token)

        r = requests.post(url = self.sf_login_url, data=data)
        if self.TestResultCode(r.status_code):
            resObj = r.json()
            self.sf_token_id = resObj["access_token"]
        
        return r
    
    def Query(self, queryString):
        
        headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
        params = {"q":queryString}
        r = requests.get(url=self.sf_query_url, headers=headers, params=params)
        records = {}
        if self.TestResultCode(r.status_code):
            resObj = r.json()
            records = resObj["records"]
            while not resObj["done"]:
                r = requests.get(url=self.sf_instance_url + "/" + resObj["nextRecordsUrl"])
                resObj = r.json()
                records.update(resObj["records"])
       
        return records

    def TestResultCode(self, rescode):
        if rescode == requests.codes.ok or rescode == requests.codes.created:
            return True

        return False

    def FindChapterLeaders(self, chapterName):
        queryString = "SELECT PagesApi__Display_Name__c,Contact_Email__c, PagesApi__Role__c FROM PagesApi__Community_Group_Member__c WHERE PagesApi__Community_Group__r.Name = '" + chapterName + "' AND PagesApi__Role__c = 'Chapter Leader'"
        records = self.Query(queryString)

        return records
        

    def FindChapter(self, chapterName):
        queryString = "SELECT Id,Name,Display_on_Membership_Application__c,City__c,Country__c FROM PagesApi__Community_Group__c WHERE Name Like '%Baltimore%'"
        records = self.Query(queryString)
        logging.info(records)
        res = ""
        if len(records) > 0:
            res = "Chapter: " + records[0]["Name"]
            res += "\n\tActive: %s" % records[0]["Display_on_Membership_Application__c"]
            Leaders = self.FindChapterLeaders(records[0]["Name"])
            res += "\n\tLeaders:"
            leader_count = len(Leaders)
            for leader in Leaders:
                res += leader["PagesApi__Display_Name__c"] + "(" + leader["Contact_Email__c"] + ")"
                leader_count -= 1
                if leader_count > 0:
                    res += ", "

            res += "\n\tMember Count:"
        else:
            res = "No chapter with name " + chapterName + " found"

        return res