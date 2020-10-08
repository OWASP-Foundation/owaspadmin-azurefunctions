import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from httplib2 import http
import json
from datetime import datetime
import random

class OWASPGoogle:
    def __init__(self):
        scopes = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/apps.groups.settings']
        client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
        creds = service_account.Credentials.from_service_account_info(client_secret, scopes=scopes)
        creds = creds.with_subject(os.environ['GOOGLE_ADMIN'])

        self.admin = build('admin', 'directory_v1', credentials=creds, cache_discovery=False)
        self.groupSettings = build('groupssettings', 'v1', credentials=creds, cache_discovery=False)

    def CreateSpecificEmailAddress(self, altemail, first, last, email_address, fail_if_exists=True):
        
        user = {
            "name": {
                "familyName": last,
                "givenName": first
            },
            "primaryEmail": email_address,
            "recoveryEmail": altemail,
            "password": datetime.now().strftime('%m%d%Y'),
            "emails": [{
                    "address": altemail,
                    "type": "home",
                    "customType": "",
                    "primary": False
                },
                {
                    "address": email_address,
                    "type": "home",
                    "customType": "",
                    "primary": True
                }
            ]
        }
        
        if fail_if_exists:
            results = self.admin.users().list(domain='owasp.org', query=f"email={user['primaryEmail']}").execute()
            if 'users' in results and len(results['users']) > 0:
                return f"User {user['primaryEmail']} already exists."

        result = f"User {user['primaryEmail']} created"
        results = self.admin.users().insert(body = user).execute()
        if 'primaryEmail' not in results:
            result = f"Failed to create User {user['primaryEmail']}."
        return result

    def CreateEmailAddress(self, altemail, first, last, fail_if_exists=True):
        
        user = {
            "name": {
                "familyName": last,
                "givenName": first,
                "fullName": first + ' ' + last
            },
            "primaryEmail": first + '.' + last + '@owasp.org',
            "recoveryEmail": altemail,
            "password": datetime.now().strftime('%m%d%Y'),
            "emails": [{
                    "address": altemail,
                    "type": "home",
                    "customType": "",
                    "primary": False
                },
                {
                    "address": first + '.' + last + '@owasp.org',
                    "type": "home",
                    "customType": "",
                    "primary": True
                }
            ]
        }
        
        if fail_if_exists:
            results = self.admin.users().list(domain='owasp.org', query=f"email={user['primaryEmail']}").execute()
            if 'users' in results and len(results['users']) > 0:
                return f"User {user['primaryEmail']} already exists."

        result = f"User {user['primaryEmail']} created"
        results = self.admin.users().insert(body = user).execute()
        if 'primaryEmail' not in results:
            result = f"Failed to create User {user['primaryEmail']}."
        return result

    def GetPossibleEmailAddresses(self, preferred_email):
        emails = []
        results = self.admin.users().list(domain='owasp.org', query=f"email={preferred_email}").execute()
        if 'users' in results and len(results['users']) > 0:
            # come up with alternates...
            random.seed()
            alternate = preferred_email[0:preferred_email.find('@'):] + f'{random.randint(1, 99)}' + preferred_email[preferred_email.find('@'):]
            results = self.admin.users().list(domain='owasp.org', query=f"email={alternate}").execute()
            if not 'users' in results:
                emails.append(alternate)
            alternate = preferred_email[0:preferred_email.find('@'):] + datetime.now().strftime("%d%m") + preferred_email[preferred_email.find('@'):]
            results = self.admin.users().list(domain='owasp.org', query=f"email={alternate}").execute()
            if not 'users' in results:
                emails.append(alternate)
            alternate = preferred_email[0:preferred_email.find('@'):] + datetime.now().strftime("%Y%m") + preferred_email[preferred_email.find('@'):]
            results = self.admin.users().list(domain='owasp.org', query=f"email={alternate}").execute()
            if not 'users' in results:
                emails.append(alternate)
            alternate = preferred_email[0] + '.' + preferred_email[preferred_email.find('.')+1:]

            results = self.admin.users().list(domain='owasp.org', query=f"email={alternate}").execute()
            if not 'users' in results:
                emails.append(alternate)
            
            if len(emails) == 0:
                emails.append('Could not find a suitable alternate email.  Please submit a ticket at https://contact.owasp.org')
                
        else: # email not in list, just give that one
            emails.append(preferred_email)

        return emails

    def FindGroup(self, group_name):
        # test if group exists...
        try:
            results = self.admin.groups().get(groupKey=group_name).execute()
            if 'name' in results:
                return results
        except:
            pass
        
        return None

    def GetGroupSettings(self, group_name):
        val = ''
        try:
            val = self.groupSettings.groups().get(groupUniqueId=group_name).execute()
        except:
            pass

        return val

    def SetGroupSettings(self, group_name, group_settings):
        val = ''
        try:
            val = self.groupSettings.groups().update(groupUniqueId=group_name, body=group_settings).execute()
        except:
            pass

        return val

    def GetGroupMembers(self, group_name):
        val = ''
        try:
            val = self.admin.members().list(groupKey=group_name).execute()
        except:
            pass

        return val

    def AddMemberToGroup(self, group_name, email, role='MANAGER', member_type='USER'):
        data = { 'email': email, 'role': role, 'type':member_type }
        val = ''
        try:
            val = self.admin.members().insert(groupKey=group_name, body=data).execute()
        except:
            pass

        return val
        

    def GetInitialGroupSettings(self):
        gs = {  'whoCanJoin': 'INVITED_CAN_JOIN', 
                'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW', 
                'whoCanViewGroup': 'ALL_MEMBERS_CAN_VIEW', 
                'whoCanInvite': 'ALL_OWNERS_CAN_INVITE', 
                'whoCanAdd': 'ALL_OWNERS_CAN_ADD', 
                'allowExternalMembers': 'true', 
                'whoCanPostMessage': 'ANYONE_CAN_POST', 
                'allowWebPosting': 'true' } 
        return gs
    
    def CreateGroup(self, group_name):
        group = {
            "adminCreated": True,
            "description": "Group Created by Automation",
            "email": group_name,
            "kind": "admin#directory#group",
            "name": "Leader Group For " + group_name
        }

        result = f"Group {group['email']} created"
        results = ''
        try:
            results = self.admin.groups().insert(body = group).execute()
        except:
            pass

        if 'name' not in results:
            result = f"Failed to create Group {group['email']}."
        else:
            self.SetGroupSettings(group_name, self.GetInitialGroupSettings())

        return result
        
    def GetActiveUsers(self, next_page_token):
        results = self.admin.users().list(domain='owasp.org', pageToken=next_page_token).execute()
        return results
