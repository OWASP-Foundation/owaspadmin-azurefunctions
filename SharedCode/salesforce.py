import requests
import json
import base64
from pathlib import Path
import os
import logging
import datetime

class OWASPSalesforce:
    sf_consumer_key = os.environ["SF_CONSUMER_KEY"]
    sf_consumer_secret = os.environ["SF_CONSUMER_SECRET"]
    sf_user_name = os.environ["SF_USER_NAME"]
    sf_user_pw = os.environ["SF_USER_PW"]
    sf_user_security_token = os.environ["SF_USER_SECURITY_TOKEN"]

    sf_login_url = "https://login.salesforce.com/services/oauth2/token"
    sf_instance_url = "https://na131.salesforce.com"
    sf_api_url = "/services/data/v46.0/"
    sf_community_group_url = "sobjects/PagesApi__Community_Group__c"
    sf_contact_url = "sobjects/Contact"
    sf_community_group_member_url = "sobjects/PagesApi__Community_Group_Member__c"
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
        chapterName = chapterName.replace("+", " ")
        queryString = "SELECT Id,Name,Display_on_Membership_Application__c,City__c,Country__c FROM PagesApi__Community_Group__c WHERE Name Like '%" + chapterName + "%'"
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


    def FindContact(self, contactName):
        contactName = contactName.replace("+", " ")
        queryString = "SELECT Id,Name,Email FROM Contact  WHERE Name Like '%" + contactName + "%'"
        records = self.Query(queryString)
        logging.info(records)
        res = ""
        for record in records:
            res += "Contact: " + record["Name"]
            res += "\n\tEmail: %s" % record["Email"]
            res += "\n"
        
        if(len(records) <= 0):
            res = "No contact with name " + contactName + " found"

        return res

    def CreateContact(self, contactName, contactEmail):
        firstname = contactName[:contactName.find(" ")]
        lastname = contactName[contactName.find(" ") + 1:]
        
        if firstname and lastname:
            jsonContact = '{ "FirstName":"' + firstname + '", "LastName":"' + lastname + '", "Email":"' + contactEmail + '", "AccountId":"0010B00001lbESTQA2" }'
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_contact_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonContact)
            if not self.TestResultCode(r.status_code):
                logging.error(r.text)

            return r
        else:
            return requests.Response("Contact creation failed: No first or last name.")
    
    def CreateCommunityGroupMember(self, leader, chapter):
        
        jsonCGM = '{ "PagesApi__Contact__c":"' + leader + '", "PagesApi__Role__c":"Chapter Leader", "PagesApi__Community_Group__c":"' + chapter + '" }'
        obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_member_url
        headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
        r = requests.post(url=obj_url, headers=headers, data=jsonCGM)
        if not self.TestResultCode(r.status_code):
            logging.error(f"Failed to create community group member: {r.text}")

        return r
        
    def CreateChapter(self, chapter_name, leader_names, leader_emails, city, country, region):
        queryString = "SELECT Id,Name,Display_on_Membership_Application__c,City__c,Country__c FROM PagesApi__Community_Group__c WHERE Name = '" + chapter_name + "'"
        records = self.Query(queryString)
        if len(records) > 0: # chapter exists already, update the chapter
            #do some things
            logging.info("Chapter exists, no need to create")
            return requests.Response("Chapter existed")
        else:
            #create a whole new chapter
            jsonChapter = '{ "Name":"' + chapter_name + '", "PagesApi__Type__c":"Chapter", "City__c":"' + city + '", "Country__c":"' + country + '", "Region__c":"' + region + '", "Display_on_Membership_Application__c":"true" }'
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonChapter)
            if not self.TestResultCode(r.status_code):
                logging.error(r.text)

            return r

        return requests.Response("Self, how did I get here?")

    def AddChapterLeader(self, leader, email, chapter_id):
        # Add stuff here
        # first do a contact lookup
        # if no contact, create contact else select contact
        # Add contact to Community Group Members as Leader type
        queryString = "SELECT Id,Name,Email FROM Contact  WHERE Name Like '%" + leader + "%'"
        records = self.Query(queryString)
        contact_id = ""
        if len(records) <= 0:
            r = self.CreateContact(leader, email)
            if not self.TestResultCode(r.status_code):
                logging.error(f"Failed to create contact: {r.text}")
                return r
            else:
                contact_json = json.loads(r.text)
                contact_id = contact_json["id"]
        else:
            contact_id = records[0]["Id"]

        r = self.CreateCommunityGroupMember(contact_id, chapter_id)
        return r
        