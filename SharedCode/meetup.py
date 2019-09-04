import requests
import json
import base64
from pathlib import Path
import os

class OWASPMeetup:
    meetup_api_url = "https://api.meetup.com"

    def Login(self):
        login_url = self.meetup_api_url