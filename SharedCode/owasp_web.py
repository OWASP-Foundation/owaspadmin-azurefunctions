import os
import logging

import requests

class OWASPWeb:
    access_token = None
    refresh_token = None

    def __init__(self):
        self.web_base_url = os.environ.get('OWASP_WEB_ENDPOINT', 'https://owasp.org/api/')
        self.base_url = self.web_base_url
                
        self.logger = logging
    
    def getBearerToken(self):
        url = f"{os.environ.get('SUPABASE_URL')}/auth/v1/token?grant_type=password"

        payload = {
            "email": os.environ.get('SUPABASE_USER_EMAIL'),
            "password": os.environ.get('SUPABASE_USER_PASSWORD')
        }

        headers = {
            "apikey": os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
            "Content-Type": "application/json"
        }

        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()

        data = r.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]

    def clearTokens(self):
        self.access_token = None
        self.refresh_token = None   

    # Chapters
    def getChapters(self):
        url = self.base_url + 'public/chapters/list?limit=1000'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Failed to get chapters: {response.status_code} - {response.text}")
        return response.json()

    def getChapterByName(self, chapter_name):
        chapters = self.getChapters()
        if chapters:
            for chapter in chapters.get('chapters', []):
                if chapter.get('name') == chapter_name:
                    return chapter
        return None

    def getChapterDetails(self, chapter_id):
        if not chapter_id:            
            return

        self.getBearerToken()
        url = self.base_url + f'admin/chapters/{chapter_id}'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'
        headers['Authorization'] = f'Bearer {self.access_token}'  # Assuming you have a method to get a valid access token
        self.clearTokens()  # Clear tokens after use
        
        chapter_details = None
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Failed to get chapter: {response.status_code} - {response.text}")
        chapter_details = response.json()
        return chapter_details


    def getChapterLeadershipTeam(self, chapter_id):
        if not chapter_id:
            return

        chapter_details = self.getChapterDetails(chapter_id)
        leadership_team = []
        if chapter_details and 'chapter' in chapter_details:
            leadership_team = chapter_details['chapter'].get('leadership_team', [])
        
        return leadership_team

    # Groups
    def getGroups(self, search=None):
        url = self.base_url + 'public/groups/list'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'
        params = {'limit': 200}
        if search:
            params['search'] = search

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            self.logger.error(f"Failed to get groups: {response.status_code}")
        return response.json()

    def getGroupByName(self, group_name):
        groups = self.getGroups()
        if groups:
            for group in groups.get('groups', []):
                if group.get('title') == group_name:
                    return group
        return None

    def getGroupDetails(self, group_id):
        if not group_id:
            return

        self.getBearerToken()
        url = self.base_url + f'admin/groups/{group_id}'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'
        headers['Authorization'] = f'Bearer {self.access_token}'
        self.clearTokens()
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Failed to get group: {response.status_code}")
        return response.json()

    def getGroupLeadershipTeam(self, group_id):
        if not group_id:
            return []

        self.getBearerToken()
        url = self.base_url + f'admin/groups/{group_id}/members'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'
        headers['Authorization'] = f'Bearer {self.access_token}'
        self.clearTokens()

        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code != 200:
            self.logger.error(f"Failed to get group members: {response.status_code}")
            return data

        return [member for member in data.get('members', []) if member.get('role') == 'admin']

    # Working Groups
    def getWorkingGroups(self):
        return self.getGroups(search='Working Group')

    def getWorkingGroupByName(self, working_group_name):
        working_groups = self.getWorkingGroups()
        if working_groups:
            for working_group in working_groups.get('groups', []):
                if working_group.get('title') == working_group_name:
                    return working_group
        return None

    def getWorkingGroupDetails(self, working_group_id):
        return self.getGroupDetails(working_group_id)

    def getWorkingGroupLeadershipTeam(self, working_group_id):
        return self.getGroupLeadershipTeam(working_group_id)

    # Committees
    def getCommittees(self):
        return self.getGroups(search='Committee')

    def getCommitteeByName(self, committee_name):
        committees = self.getCommittees()
        if committees:
            for committee in committees.get('groups', []):
                if committee.get('title') == committee_name:
                    return committee
        return None

    def getCommitteeDetails(self, committee_id):
        return self.getGroupDetails(committee_id)

    def getCommitteeLeadershipTeam(self, committee_id):
        return self.getGroupLeadershipTeam(committee_id)

    #Projects
    def getProjects(self):
        url = self.base_url + 'public/projects/list?limit=1000'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Failed to get projects: {response.status_code} - {response.text}")
        return response.json()

    def getProjectByName(self, project_name):
        projects = self.getProjects()
        if projects:
            for project in projects.get('projects', []):
                if project.get('title') == project_name:
                    return project    
        return None

    def getProjectDetails(self, project_id):
        if not project_id:            
            return

        self.getBearerToken()
        url = self.base_url + f'admin/projects/{project_id}'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'
        headers['Authorization'] = f'Bearer {self.access_token}'  # Assuming you have a method to get a valid access token
        self.clearTokens()  # Clear tokens after use
        
        project_details = None
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Failed to get project: {response.status_code} - {response.text}")
        project_details = response.json()
        return project_details

    def getProjectLeadershipTeam(self, project_id):
        if not project_id:
            return

        project_details = self.getProjectDetails(project_id)
        leadership_team = []
        if project_details and 'project' in project_details:
            leadership_team = project_details['project'].get('project_leaders', [])
        
        return leadership_team