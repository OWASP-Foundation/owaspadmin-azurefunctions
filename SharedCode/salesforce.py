import requests
import json
import base64
from pathlib import Path
import os
import logging
import datetime
import locale

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
    sf_account_url = "sobjects/Account"
    sf_community_group_member_url = "sobjects/PagesApi__Community_Group_Member__c"
    sf_subscription_url = "sobjects/OrderApi__Subscription__c"
    sf_sales_order_url = "sobjects/OrderApi__Sales_Order__c"
    sf_sales_order_line_url = "sobjects/OrderApi__Sales_Order_Line__c"
    sf_receipt_url = "sobjects/OrderApi__Receipt__c"
    sf_receipt_line_url = "sobjects/OrderApi__Receipt_Line__c"
    sf_badge_url = "sobjects/OrderApi__Badge__c"
    sf_token_id = ""
    sf_query_url = sf_instance_url + sf_api_url + "query"

    ONE_YEAR_MEMBERSHIP = os.environ['SF_ONE_YEAR_MEMBERSHIP']
    STUDENT_MEMBERSHIP = os.environ['SF_STUDENT_MEMBERSHIP']
    STUDENT_WORKFLOW = os.environ['SF_STUDENT_WORKFLOW']
    STUDENT_BADGE = os.environ['SF_STUDENT_BADGE']
    UNKNOWN_ACCOUNT = os.environ['SF_UNKNOWN_ACCOUNT']
    ITEM_CLASS_MEMBERSHIP = os.environ['SF_ITEM_CLASS_MEMBERSHIP']
    GL_ACCOUNT = os.environ['SF_GL_ACCOUNT']
    PAYMENT_GATEWAY = os.environ['SF_PAYMENT_GATEWAY']

    def Login(self):
        data = dict(grant_type='password',
                    client_id=self.sf_consumer_key,
                    client_secret=self.sf_consumer_secret,
                    username=self.sf_user_name,
                    password=self.sf_user_pw + self.sf_user_security_token)

        r = requests.post(url = self.sf_login_url, data=data)
        if r.ok:
            resObj = r.json()
            self.sf_token_id = resObj["access_token"]
        
        return r
    
    def Query(self, queryString):
        
        headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
        params = {"q":queryString}
        r = requests.get(url=self.sf_query_url, headers=headers, params=params)
        records = {}
        if r.ok:
            resObj = r.json()
            records = resObj["records"]
            while not resObj["done"]:
                r = requests.get(url=self.sf_instance_url + "/" + resObj["nextRecordsUrl"])
                resObj = r.json()
                records.update(resObj["records"])
       
        return records

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
    
    def FindContactRecord(self, contactName, email):
        contactName = contactName.replace("+", " ")
        queryString = f"SELECT Id,Name,Email FROM Contact  WHERE Name Like '%{contactName}%' and Email='{email}'"
        records = self.Query(queryString)
    
        return records

    def CreateContact(self, contactName, contactEmail, accountId = None):
        firstname = contactName[:contactName.find(" ")]
        lastname = contactName[contactName.find(" ") + 1:]
        if not accountId:
            accountId = self.UNKNOWN_ACCOUNT
        if firstname and lastname:
            jsonContact = '{ "FirstName":"' + firstname + '", "LastName":"' + lastname + '", "Email":"' + contactEmail + '", "AccountId":"' + accountId + '" }'
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_contact_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonContact)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Contact creation failed: No first or last name.", 400)

    def CreateAccount(self, accountName):        
        if accountName:
            jsonAccount = '{ "Name":"' + accountName + '"}'
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_account_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonAccount)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Account creation failed: No name.", 400)
    
    def CreateSubscription(self, contact, account, mtype, plan):        
        if contact:
            jsonSubscription = '{ "OrderApi__Account__c":"' + account + '", "OrderApi__Contact__c":"' + contact + '", "OrderApi__Item__c":"' + mtype + '", "OrderApi__Subscription_Plan__c":"' + plan + '" }'
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_subscription_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonSubscription)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Subscription creation failed: No contact.", 400)

    def CreateSalesOrder(self, contact):        
        if contact:
            jsonSalesOrder = {}
            jsonSalesOrder['OrderApi__Contact__c'] = contact
            jsonSalesOrder['OrderApi__Entity__c'] = 'Contact'
            jsonSalesOrder['OrderApi__Status__c'] = 'Open'
            #jsonSalesOrder['OrderApi__Posting_Status__c'] = 'Pending'

            jsonString = json.dumps(jsonSalesOrder)

            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_sales_order_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Sales order creation failed: No contact.", 400)
    
    def PostSalesOrder(self, sorder_id):        
        if sorder_id:
            jsonSalesOrder = {}
            jsonSalesOrder['OrderApi__Status__c'] = 'Closed'
            jsonSalesOrder['OrderApi__Posting_Status__c'] = 'Posted'
            jsonSalesOrder['OrderApi__Closed_Status__c'] = 'Cash Sale'
            jsonString = json.dumps(jsonSalesOrder)

            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_sales_order_url + f'/{sorder_id}'
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.patch(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Sales order update failed: No sales order id.", 400)

    def CreateSalesOrderLine(self, contact, order_id, type_id, plan_id, class_id, line_desc):        
        if contact:
            jsonSalesOrder = {}
            jsonSalesOrder['OrderApi__Contact__c'] = contact
            jsonSalesOrder['OrderApi__Entity__c'] = 'Contact'
            jsonSalesOrder['OrderApi__Item_Class__c'] = class_id
            jsonSalesOrder['OrderApi__Item__c'] = type_id
            jsonSalesOrder['OrderApi__Sales_Order__c'] = order_id
            jsonSalesOrder['OrderApi__Line_Description__c'] = line_desc
            jsonSalesOrder['OrderApi__Subscription_Plan__c'] = plan_id

            jsonString = json.dumps(jsonSalesOrder)

            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_sales_order_line_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Sales order creation failed: No contact.", 400)

    def CreateReceipt(self, contact, transaction_id, type_id, plan_id, amount):        
        if contact:
            jsonReceipt = {}
            jsonReceipt['OrderApi__Contact__c'] = contact
            jsonReceipt['OrderApi__Entity__c'] = 'Contact'
            jsonReceipt['OrderApi__Type__c'] = 'Payment'
            jsonReceipt['OrderApi__Deposit_Account__c'] = self.GL_ACCOUNT
            jsonReceipt['OrderApi__Payment_Gateway__c'] = self.PAYMENT_GATEWAY
            jsonReceipt['OrderApi__Payment_Type__c'] = 'Other'
            jsonReceipt['OrderApi__Reference_Number__c'] = transaction_id
            jsonReceipt['OrderApi__Total__c'] = amount
            jsonReceipt['OrderApi__Is_Posted__c'] = 1
            jsonString = json.dumps(jsonReceipt)

            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_receipt_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(f'Failed to create receipt: {r.text}')
            else:
                jsonRcpt = json.loads(r.text)
                rcpt_id = jsonRcpt['id']
                jsonLine = {}
                jsonLine['OrderApi__Receipt__c'] = rcpt_id
                jsonLine['OrderApi__Item__c'] = type_id
                jsonLine['OrderApi__Subscription_Plan__c'] = plan_id
                jsonString = json.dumps(jsonLine)

                obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_receipt_line_url
                headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
                r = requests.post(url=obj_url, headers=headers, data=jsonString)
                if not r.ok:
                    logging.error(f'Failed to create receipt: {r.text}')

            return r
        else:
            return requests.Response("Sales order creation failed: No contact.", 400)

    def CreateBadge(self, contact, type_id, sales_order_id):        
        if contact:
            badge_type = None
            if type_id == self.STUDENT_MEMBERSHIP:
                badge_type = self.STUDENT_BADGE

            jsonBadge = {}
            jsonBadge['OrderApi__Contact__c'] = contact
            jsonBadge['OrderApi__Badge_Type__c'] = badge_type
            jsonBadge['OrderApi__Item__c'] = type_id
            jsonBadge['OrderApi__Sales_Order_Line__c'] = sales_order_id
            jsonBadge['OrderApi__Awarded_Date__c'] = datetime.date.today().strftime('%Y-%m-%d')
            jsonString = json.dumps(jsonBadge)
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_badge_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(r.text)

            return r
        else:
            return requests.Response("Subscription creation failed: No contact.", 400)

    def CreateCommunityGroupMember(self, leader, group, role):
        jsonCGM = {}
        jsonCGM['PagesApi__Contact__c'] = leader
        jsonCGM['PagesApi__Role__c'] = role
        jsonCGM['PagesApi__Community_Group__c'] = group
        jsonString = json.dumps(jsonCGM)
        
        records = self.Query(f'SELECT Id, Name WHERE PagesApi__Contact__c="{leader}" AND PagesApi__Role__c="{role}" AND PagesApi__Community_Group__c="{group}"')
        if len(records) > 0:
            cgmem_id = records[0]['Id']
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_member_url + '/' + cgmem_id
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.get(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(f"Failed to create community group member: {r.text}")
        else:
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_member_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(f"Failed to create community group member: {r.text}")

        return r
        
    def CreateChapter(self, chapter_name, leader_names, leader_emails, city, country, region):
        queryString = "SELECT Id,Name,Display_on_Membership_Application__c,City__c,Country__c FROM PagesApi__Community_Group__c WHERE Name = '" + chapter_name + "'"
        records = self.Query(queryString)
        if len(records) > 0: # chapter exists already, update the chapter
            #do some things
            logging.info("Chapter exists, no need to create")
            ch_id = records[0]['Id']
            # need to query chapter record from API....
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_url + '/' + ch_id
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.get(url=obj_url, headers=headers)
            if not r.ok:
                logging.error(r.text)

            return r    
        else:
            #create a whole new chapter
            jsonChapter = '{ "Name":"' + chapter_name + '", "PagesApi__Type__c":"Chapter", "City__c":"' + city + '", "Country__c":"' + country + '", "Region__c":"' + region + '", "Display_on_Membership_Application__c":"true" }'
            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonChapter)
            if not r.ok:
                logging.error(r.text)

            return r

        return requests.Response("Self, how did I get here?", 400)

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
            if not r.ok:
                logging.error(f"Failed to create contact: {r.text}")
                return r
            else:
                contact_json = json.loads(r.text)
                contact_id = contact_json["id"]
        else:
            contact_id = records[0]["Id"]

        r = self.CreateCommunityGroupMember(contact_id, chapter_id, 'Chapter Leader')
    
        return r
    
    def CreateProject(self, project_name, leader_names, leader_emails):
        project_name = 'OWASP ' + project_name
        queryString = "SELECT Id,Name,Display_on_Membership_Application__c,City__c,Country__c FROM PagesApi__Community_Group__c WHERE Name = '" + project_name + "'"
        records = self.Query(queryString)
        if len(records) > 0: # chapter exists already, update the chapter
            #do some things
            logging.info("Project exists, no need to create")
            return requests.Response("Project existed", 400)
        else:
            #create a whole new chapter
            jsonProject = {}
            jsonProject['Name'] = project_name
            jsonProject['PagesApi__Type__c'] = 'Project'
            jsonProject['Display_on_Membership_Application__c'] = 1
            jsonString = json.dumps(jsonProject)

            obj_url =    self.sf_instance_url + self.sf_api_url + self.sf_community_group_url
            headers = {"Content-Type":"application/json", "Authorization":"Bearer " + self.sf_token_id, "X-PrettyPrint":"1" }
            r = requests.post(url=obj_url, headers=headers, data=jsonString)
            if not r.ok:
                logging.error(r.text)

            return r

        return requests.Response("Self, how did I get here?", 400)

    def AddProjectLeader(self, leader, email, project_id):
        # Add stuff here
        # first do a contact lookup
        # if no contact, create contact else select contact
        # Add contact to Community Group Members as Leader type
        queryString = "SELECT Id,Name,Email FROM Contact  WHERE Name Like '%" + leader + "%'"
        records = self.Query(queryString)
        contact_id = ""
        if len(records) <= 0:
            r = self.CreateContact(leader, email)
            if not r.ok:
                logging.error(f"Failed to create contact: {r.text}")
                return r
            else:
                contact_json = json.loads(r.text)
                contact_id = contact_json["id"]
        else:
            contact_id = records[0]["Id"]

        r = self.CreateCommunityGroupMember(contact_id, project_id, 'Project Leader')
    
        return r

    def GenerateSubscription(self, firstname, lastname, email, account, transaction_id, amount, merchant_type, type_id, plan_id, line_desc):
        # so many things here....
        # find a subscription of the same type and plan
        # if exists, add Term
        # else, create new and add Term
        # Create Sales Order and Sales Order Line
        # Create Receipt
        account_id = None
        contact_id = None
        records = self.Query(f"Select Id from Account Where Name = '{account}'")
        if len(records) > 0:
            account_id = records[0]["Id"]
        else:
            r = self.CreateAccount(account)
            if r.ok:
                acc_json = json.loads(r.text)
                account_id = acc_json['id']
            else:
                logging.error(f'Could not create account for {account}: {r.text}')
        
        if not account_id:
            return False

        records = self.FindContactRecord(f'{firstname} {lastname}', email)
        if len(records) > 0:
            contact_id = records[0]['Id']
        else:
            r = self.CreateContact(f'{firstname} {lastname}', email, account_id)
            if r.ok:
                cg_json = json.loads(r.text)
                contact_id = cg_json['id']
            else:
                logging.error(f'Failed to create contact: {r.text}')

        if not contact_id:
            return False

        # subscription_id = None        
        # records = self.Query(f"select Id, OrderApi__Current_Term_End_Date__c from OrderApi__Subscription__c where Contact = '{contact_id}' and OrderApi__Subscription_Plan__c = '{plan_id}' and OrderApi__Item__c = '{type_id}' order by OrderApi__Current_Term_End_Date__c desc")
        # if len(records) > 0:
        #     subscription_id = records[0]['Id']
        # else:
        #     r = self.CreateSubscription(contact_id, account_id, type_id, plan_id)
        #     if r.ok:
        #         s_json = json.loads(r.text)
        #         subscription_id = s_json['id']
        #     else:
        #         logging.error(f'Failed to create subscription: {r.text}')
        
        # if not subscription_id:
        #     return False

        # creating the sales order and posting it creates everything dealing with subscription
        sorder_id = None
        r = self.CreateSalesOrder(contact_id)  
        if r.ok:
            sojson = json.loads(r.text)
            sorder_id = sojson['id']
        else:
            logging.error(f'Failed to create sales order: {r.text}')
        
        if not sorder_id:
            return False
        
        sorder_li_id = None
        r = self.CreateSalesOrderLine(contact_id, sorder_id, type_id, plan_id, self.ITEM_CLASS_MEMBERSHIP, line_desc)
        if r.ok:
            sojson = json.loads(r.text)
            sorder_li_id = sojson['id']
        else:
            logging.error(f'Failed to create sales order line: {r.text}')
        
        if not sorder_li_id:
            return False
        
        r = self.CreateReceipt(contact_id, transaction_id, type_id, plan_id, amount)
        if not r.ok:
            logging.warn(f'Failed to create receipt: {r.text}')
        
        # Badge created by post as well
        # r = self.CreateBadge(contact_id, type_id, sorder_li_id)
        # if not r.ok:
        #     logging.warn(f'Failed to create badge: {r.text}')
        
        r = self.PostSalesOrder(sorder_id)
        if not r.ok:
            logging.warn(f'Failed to update sales order: {r.text}')

        return True

    def GenerateStudentSubscription(self, firstname, lastname, email, university, transaction_id, merchant_type):
        return self.GenerateSubscription(firstname, lastname, email, university, transaction_id, 20.00, merchant_type, self.STUDENT_MEMBERSHIP, self.ONE_YEAR_MEMBERSHIP, 'Student Membership')
            