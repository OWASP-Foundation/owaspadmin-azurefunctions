import os
import sys
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode
from datetime import datetime
from datetime import timedelta

def make_token(message):
    fernet_key = os.environ["BILLING_ENCRYPTION_KEY"]
    expiration = datetime.now() + timedelta(days=1)
    expiration = expiration.strftime('%m/%d/%Y')

    token_unencrypted = message + '|' + expiration

    f = Fernet(fernet_key)
    token = f.encrypt(token_unencrypted.encode())

    return token


def decode_token(token):
    fernet_key = os.environ["BILLING_ENCRYPTION_KEY"]
    f = Fernet(fernet_key)
    unencrypted = f.decrypt(token.encode())

    text_array = unencrypted.decode().split('|')
    return text_array[0]
