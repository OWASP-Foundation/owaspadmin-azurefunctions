import os
import io
import requests

class OWASPZoom:
    base_url = 'https://api.zoom.us/v2/'
    user_url = 'users/'

    def GetHeaders(self):
        headers = {
            'authorization': 'Bearer ' + os.environ['ZOOM_JWT_TOKEN']
        }

        return headers

    def GetUser(self, user_id = None):
        if user_id == None:
            user_id = 'me'
        r = requests.get(self.base_url + self.user_url + user_id, headers=self.GetHeaders())
        if r.ok:
            return r.text
        else:
            return ''