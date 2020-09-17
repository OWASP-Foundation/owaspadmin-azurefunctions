import os.path
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import json

def create_email_address(altemail, first, last):
    scope = ['https://www.googleapis.com/auth/admin.directory.user']
    client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(client_secret, scope)

    admin = build('admin', 'directory_v1', credentials=creds, cache_discovery=False)
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
    return admin.users().insert(body = user)