import requests
import json
import os

class OWASPCopper:

    cp_base_url = "https://api.prosperworks.com/developer_api/v1/"
    cp_projects_fragment = "projects/"
    cp_opp_fragment = "opportunities/"
    cp_people_fragment = "people/"
    cp_related_fragment = ':entity/:entity_id/related'
    cp_custfields_fragment = 'custom_field_definitions/'
    cp_search_fragment = "search"
    
    # Custom Field Definition Ids
    cp_project_type = 399609
    cp_project_type_option_global_event = 899314
    cp_project_type_option_regional_event = 899315
    cp_project_type_option_chapter = 899316
    cp_project_type_option_global_partner = 900407
    cp_project_type_option_local_partner = 900408
    cp_project_type_option_project = 1378082
    cp_project_type_option_committee = 1378083
    cp_project_github_repo = 399740
    # event specific
    cp_project_event_start_date = 392473
    cp_project_event_website = 395225
    cp_project_event_sponsorship_url = 395226
    cp_project_event_projected_revenue = 392478
    cp_project_event_sponsors = 392480
    cp_project_event_jira_ticket = 394290
    cp_project_event_approved_date = 392477
    # chapter specific
    cp_project_chapter_status = 399736
    cp_project_chapter_status_option_active = 899462
    cp_project_chapter_status_option_inactive = 899463
    cp_project_chapter_status_option_suspended = 899464
    cp_project_chapter_region = 399739
    cp_project_chapter_region_option_africa = 899465
    cp_project_chapter_region_option_asia = 899466
    cp_project_chapter_region_option_europe = 899467
    cp_project_chapter_region_option_northamerica = 899468
    cp_project_chapter_region_option_oceania = 899469
    cp_project_chapter_region_option_southamerica = 899470
    cp_project_chapter_country = 399738
    cp_project_chapter_postal_code = 399737

    def GetHeaders(self):
        headers = {
            'X-PW-AccessToken':os.environ['COPPER_API_KEY'],
            'X-PW-Application':'developer_api',
            'X-PW-UserEmail':os.environ['COPPER_USER'],
            'Content-Type':'application/json'
        }
        return headers

    def ListProjects(self):
        data = {
            'page_size': 200,
            'sort_by': 'name'
        }
        url = f'{self.cp_base_url}{self.cp_projects_fragment}{self.cp_search_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text
        
        return ''
        
    def ListOpportunities(self):
        data = {
            'page_size': 200,
            'sort_by': 'name'
        }
        url = f'{self.cp_base_url}{self.cp_opp_fragment}{self.cp_search_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text
        
        return ''
        
    def FindPersonByEmail(self, searchtext):
        lstxt = searchtext.lower()
        if len(lstxt) <= 0:
            return ''

        data = {
            'page_size': 5,
            'sort_by': 'name',
            'emails': [lstxt]
        }

        url = f'{self.cp_base_url}{self.cp_people_fragment}{self.cp_search_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text
        
        return ''

    def FindPersonByName(self, searchtext):
        lstxt = searchtext.lower()
        if len(lstxt) <= 0:
            return ''
            
        data = {
            'page_size': 5,
            'sort_by': 'name',
            'name': lstxt
        }

        url = f'{self.cp_base_url}{self.cp_people_fragment}{self.cp_search_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text
        
        return ''

    def CreatePerson(self, email):
        data = {
            'emails': [
                {
                    'email':email,
                    'category': 'work'
                }
            ]
        }
        url = f'{self.cp_base_url}{self.cp_people_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        pid = None
        if r.ok:
            person = json.loads(r.text)
            pid = person.id
        
        return pid

    def CreateOpportunity(self, opp_name, contact_email):

        contact_json = self.FindPersonByEmail(contact_email)
        if contact_json == '':
            return ''
        people = json.loads(contact_json)

        # See CreateProject for adding custom fields
        
        data = {
            'name': 'opp_name',
            'primary_contact_id': people[0]['id']
        }

        url = f'{self.cp_base_url}{self.cp_opp_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text
        
        return ''

    def GetProject(self, proj_name):
        data = {
            'page_size': 200,
            'sort_by': 'name',
            'name': proj_name, 
        }
        url = f'{self.cp_base_url}{self.cp_projects_fragment}{self.cp_search_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text
        
        return ''

    def RelateRecord(self, entity, entity_id, person_id):
        data = {
            'resource': {
                'id': person_id,
                'type': 'person'
            }
        }
        url = f'{self.cp_base_url}{self.cp_related_fragment}'
        url = url.replace(':entity_id', str(entity_id)).replace(':entity', entity)
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            return r.text

        return ''

    def FindProject(self, proj_name):
        lstxt = proj_name.lower()

        data = {
            'page_size': 5,
            'sort_by': 'name',
            'name': lstxt
        }
        projects = []
        url = f'{self.cp_base_url}{self.cp_projects_fragment}{self.cp_search_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            projects = json.loads(r.text)
            return projects
        
        return projects

    def CreateProject(self, proj_name, emails, project_type, status, region, country, postal_code, repo):
        data = {
                'name':proj_name
        }
        fields = []
        if project_type:
            fields.append({
                    'custom_field_definition_id' : self.cp_project_type, 
                    'value': project_type
                })
        if status:
            fields.append({
                    'custom_field_definition_id': self.cp_project_chapter_status,
                    'value': status
                })
        if region:
            fields.append({
                    'custom_field_definition_id': self.cp_project_chapter_region,
                    'value': region
                })
        if country:
            fields.append({
                    'custom_field_definition_id': self.cp_project_chapter_country,
                    'value': country
                })
        if postal_code:
            fields.append({
                    'custom_field_definition_id': self.cp_project_chapter_postal_code,
                    'value': postal_code
                })
        fields.append({
                    'custom_field_definition_id': self.cp_project_github_repo,
                    'value': repo
                })
                
        custom_fields = fields

        data['custom_fields'] = custom_fields

        url = f'{self.cp_base_url}{self.cp_projects_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            project = json.loads(r.text)
            pid = project['id']

            for email in emails:
                sr = self.FindPersonByEmail(email)
                people = json.loads(sr)
                if len(people) > 0:
                    person_id = people[0]['id']
                else: 
                    person_id = self.CreatePerson(email)    
                
                if person_id:
                    self.RelateRecord('projects', pid, person_id)


            return r.text
        
        return ''

    def GetCustomFields(self):
        url = f'{self.cp_base_url}{self.cp_custfields_fragment}'
        r = requests.get(url, headers=self.GetHeaders())
        if r.ok:
            return r.text
        
        return ''