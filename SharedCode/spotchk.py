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

