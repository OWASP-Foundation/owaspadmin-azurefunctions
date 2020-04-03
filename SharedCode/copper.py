import requests
import json
import os

# Not currently a full implementation - does not, for instance, go through pages of Objects (limited to the first 200 right now)
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

    # Provide a list (first 200) of Projects (these are Groups & Events)
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

    # Provide a list (first 200) of Opportunities (these can be true opportunities, memberships, event attendees)
    # Needs to be modified to accept a type and pull only that type
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
    
    # Finds a Person by email address.  Will return the first 5 matches
    def FindPersonByEmail(self, searchtext):
        lstxt = searchtext.lower()

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

    # Finds a person by the full name.  Will return the first 5 matches.
    def FindPersonByName(self, searchtext):
        lstxt = searchtext.lower()

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

    # Creates an Opportunity
    # Needs to be modified to add custom fields (like type)
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

    # Finds a project by name.  Returns the first 200 results
    def FindProject(self, proj_name):
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

    # Relates a Person Record to another entity
    # Could be modified to allow a type argument to relate and record type to another entity
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

    # Create a Project (Chapter or Event or some other Group)
    # The emails, region, country, postal code are all specific to Chapter so
    # it may be beneficial to call this CreateChapter and create another function for Event
    def CreateProject(self, proj_name, emails, status, region, country, postal_code, repo):
        data = {
                'name':proj_name
        }
        custom_fields = [{
                    'custom_field_definition_id': self.cp_project_type,
                    'value': self.cp_project_type_option_chapter
                },
                {
                    'custom_field_definition_id': self.cp_project_chapter_status,
                    'value': status
                }
                ,
                {
                    'custom_field_definition_id': self.cp_project_chapter_region,
                    'value': region
                },
                {
                    'custom_field_definition_id': self.cp_project_chapter_country,
                    'value': country
                },
                {
                    'custom_field_definition_id': self.cp_project_chapter_postal_code,
                    'value': postal_code
                },
                {
                    'custom_field_definition_id': self.cp_project_github_repo,
                    'value': repo
                }
                ]

        data['custom_fields'] = custom_fields

        url = f'{self.cp_base_url}{self.cp_projects_fragment}'
        r = requests.post(url, headers=self.GetHeaders(), data=json.dumps(data))
        if r.ok:
            project = json.loads(r.text)
            pid = project['id']

            for email in emails:
                sr = self.FindPersonByEmail(email)
                if len(sr) > 0:
                    person_id = json.loads(sr)[0]['id']
                    self.RelateRecord('projects', pid, person_id)

            return r.text
        
        return ''

    # Assistant function that returns ALL custom fields.  
    # This class could be updated such that the custom field definition at the front of the
    # class could go away and these returned fields could be used to look up the fields.
    # Alternately, add classes for all the types (better)
    def GetCustomFields(self):
        url = f'{self.cp_base_url}{self.cp_custfields_fragment}'
        r = requests.get(url, headers=self.GetHeaders())
        if r.ok:
            return r.text
        
        return ''