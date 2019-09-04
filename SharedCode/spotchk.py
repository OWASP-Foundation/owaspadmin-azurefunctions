import os

class spotchk:

    def validate_query(self, md5str):
        salt_secret = os.environ['SL_TEAM']
        salt_provider = os.environ['SL_RURL']
        salt_bind = os.environ['SL_COMM']
        salt_la = os.environ['SL_LAV']

        testsec = md5str[os.environ['P_SECRET']]
        testprov = md5str[os.environ['P_PROVIDER']]
        testcomm = md5str[os.environ['P_COMM']]
        testla = md5str[os.environ['P_LAV']]
        # minor annoyance for unofficial callers
        return testsec == salt_secret and testprov.find(salt_provider) >= 0 and testcomm == salt_bind and testla == salt_la

