import os

class spotchk:

    def validate_query(self, md5str):
        try:
            salt_secret = os.environ['SL_TEAM']
            salt_provider = os.environ['SL_RURL']
            salt_bind = os.environ['SL_COMM']
            
            testsec = md5str[os.environ['P_SECRET']]
            testprov = md5str[os.environ['P_PROVIDER']]
            testcomm = md5str[os.environ['P_COMM']]
            
            salt_la = os.environ['SL_LAV']
            testla =  os.environ['P_LAV']
        
        except KeyError:
            return False

        # minor annoyance for unofficial callers
        return testsec == salt_secret and testprov.find(salt_provider) >= 0 and testcomm == salt_bind and testla == salt_la

