import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from httplib2 import http
import json


class OWASPGoogle:
    def CreateEmailAddress(self, altemail, first, last, fail_if_exists=True):
        scopes = ['https://www.googleapis.com/auth/admin.directory.user']
        client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
        creds = service_account.Credentials.from_service_account_info(client_secret, scopes=scopes)
        creds = creds.with_subject(os.environ['GOOGLE_ADMIN'])

        admin = build('admin', 'directory_v1', credentials=creds)
        
        user = {
            "name": {
                "familyName": last,
                "givenName": first,
                "fullName": first + ' ' + last
            },
            "primaryEmail": first + '.' + last + '@owasp.org',
            "recoveryEmail": altemail,
            "password": "@123OWASP123@"
        }
        
        if fail_if_exists:
            results = admin.users().list(domain='owasp.org', query=f"email={user['primaryEmail']}").execute()
            if 'users' in results and len(results['users']) > 0:
                return f"User {user['primaryEmail']} already exists."

        result = f"User {user['primaryEmail']} created"
        results = admin.users().insert(body = user).execute()
        if 'primaryEmail' not in results:
            result = f"Failed to create User {user['primaryEmail']}."

        return results