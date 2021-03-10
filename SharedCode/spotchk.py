import os

class spotchk:

    def validate_query(self, md5str):
        try:
            salt_secret = os.environ['SL_TEAM']
            salt_provider = os.environ['SL_RURL']
            
            testsec = md5str[os.environ['P_SECRET']]
            testprov = md5str[os.environ['P_PROVIDER']]
            
            salt_la = os.environ['SL_LAV']
            testla =  os.environ['P_LAV']

            sl_token = os.environ["SL_TOKEN"]
            md5_token = md5str[os.environ["SL_CHECK"]]

        except KeyError:
            return False

        # minor annoyance for unofficial callers
        return testsec == salt_secret and testprov.find(salt_provider) >= 0 and testla == salt_la and sl_token == md5_token

    def validate_query2(self, md5str):
        try:
            salt_secret = os.environ['SL_TEAM_GENERAL']
            salt_provider = os.environ['SL_RURL']
            
            testsec = md5str[os.environ['P_SECRET']]
            testprov = md5str[os.environ['P_PROVIDER']]
            
            salt_la = os.environ['SL_LAV']
            testla =  os.environ['P_LAV']

            sl_token = os.environ["SL_TOKEN_GENERAL"]
            md5_token = md5str[os.environ["SL_CHECK"]]

            sl_sgchannel = os.environ['SL_STAFF_GENERAL']
            sl_sechannel = os.environ['SL_STAFF_EVENTS']
            channel = md5str['channel_id']
        except KeyError:
            return False

        # minor annoyance for unofficial callers
        return testsec == salt_secret and testprov.find(salt_provider) >= 0 and testla == salt_la and sl_token == md5_token and (sl_sgchannel == channel or sl_sechannel == channel)

