import json

import requests
import os
import logging
import time
import hmac
import hashlib

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

    def getChapters(self):
        url = self.base_url + 'public/chapters/list?limit=4000'
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        headers['Accept'] = 'application/json'
        headers['Cache-Control'] = 'no-cache'

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to get chapters: {response.status_code} - {response.text}")
            return None

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
        if response.status_code == 200:
            chapter_details = response.json()                                
            
        return chapter_details


    def getLeadershipTeam(self, chapter_id):
        if not chapter_id:
            return

        chapter_details = self.getChapterDetails(chapter_id)
        leadership_team = None
        if chapter_details and 'chapter' in chapter_details:
            leadership_team = chapter_details['chapter'].get('leadership_team', [])            
        
        return leadership_team
    