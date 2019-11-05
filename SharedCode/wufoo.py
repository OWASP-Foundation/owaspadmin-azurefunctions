import requests
import json
import base64
from pathlib import Path
import os
import logging

class OWASPWufoo:
    apitoken = os.environ["WF_APIKEY"]
    baseurl = "https://owasp.wufoo.com/api/v3/forms/"

    OPERATOR_CONTAINS = 'Contains'
    OPERATOR_NOT_CONTAINS = 'Does_not_contain'
    OPERATOR_BEGINS_WITH = 'Begins_with'
    OPERATOR_ENDS_WITH = 'Ends_with'
    OPERATOR_LESS_THAN = 'Is_less_than'
    OPERATOR_GREATER_THAN = 'Is_greater_than'
    OPERATOR_ON = 'Is_on' 
    OPERATOR_BEFORE = 'Is_before'
    OPERATOR_AFTER = 'Is_after'
    OPERATOR_NOT_EQUAL = "Is_not_equal_to"
    OPERATOR_EQUAL = 'Is_equal_to'
    OPERATOR_EXISTS = 'Is_not_NULL'

    FIRST_NAME_FIELD = 'Field148'
    LAST_NAME_FIELD = 'Field149'
    EMAIL_FIELD = 'Field10'
    MEMBERSHIP_TYPE_FIELD = 'Field260'
    COUNTRY_FIELD = 'Field13'
    POSTAL_CODE_FIELD = 'Field11'
    UNIVERSITY_FIELD = 'Field262'
    GRADUATION_DATE_FIELD = 'Field264'
    FAVORITE_CLASS_FIELD = 'Field265'
    DATE_CREATED_FIELD = 'DateCreated'
    HANDSHAKE_KEY_FIELD = 'HandshakeKey'
    STATUS_FIELD = "Status"

    def GetFieldFromFormEntry(self, form, fieldid, operator, param):
        #https://owasp.wufoo.com/api/v3/forms/join-owasp-as-a-student/entries.xml?Filter1=EntryId+Is_equal_to+3
        strtpass = f'{self.apitoken}:{os.environ["WF_APIPASS"]}'
        auth = base64.b64encode(strtpass.encode('utf-8')).decode('utf-8')
        headers = { 'Authorization': f'Basic { auth }' }
        url = f'{self.baseurl}{form}/entries.json?system=1&Filter1={fieldid}+{operator}+{param}'
        result = ''
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            jsonEntries = json.loads(r.text)
            if len(jsonEntries) > 0: 
                jsonEntry = jsonEntries['Entries'][0]
                result = jsonEntry[fieldid]

        return result


    def GetPaidField(self, form, email, datecreated):
        strtpass = f'{self.apitoken}:{os.environ["WF_APIPASS"]}'
        auth = base64.b64encode(strtpass.encode('utf-8')).decode('utf-8')
        headers = { 'Authorization': f'Basic { auth }' }
        url = f'{self.baseurl}{form}/entries.json?system=1&Filter1={self.EMAIL_FIELD}+{self.OPERATOR_EQUAL}+{email}&Filter2={self.DATE_CREATED_FIELD}+{self.OPERATOR_ON}+{datecreated}'
        result = ''
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            jsonEntries = json.loads(r.text)
            if len(jsonEntries['Entries']) > 0: # There should be only one entry with the same email and datecreated but these idiots do not support is equal to for date...
                for jsonEntry in jsonEntries['Entries']:
                    result = jsonEntry[self.STATUS_FIELD]
                    if 'Completed' in result:
                        break

        return result

            
        






