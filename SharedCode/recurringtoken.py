import os
import sys
from simplecrypt import encrypt, decrypt
from base64 import b64encode, b64decode
from datetime import datetime
from datetime import timedelta

def make_token(message):
    password = os.environ["BILLING_ENCRYPTION_KEY"]
    expiration = datetime.now() + timedelta(days=1)
    expiration = expiration.strftime('%m/%d/%Y')
    cipher = encrypt(password, message + '|' + expiration)
    encoded_cipher = b64encode(cipher)
    return encoded_cipher.decode('utf-8')


def decode_token(token):
    password = os.environ["BILLING_ENCRYPTION_KEY"]

    cipher = b64decode(token)
    plaintext = decrypt(password, cipher)
    plaintext = plaintext.decode('utf-8')
    text_array = plaintext.split('|')
    return text_array[0]
