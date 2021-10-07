import logging
import json
import azure.functions as func
from datetime import datetime
from ..SharedCode import helperfuncs
from ..SharedCode import googleapi
import stripe
import os

stripe.api_key = os.environ["STRIPE_SECRET"]


def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    data = json.loads(msg.get_body().decode('utf-8'))
    user_email = data.get('email', None)

    og = googleapi.OWASPGoogle()
    if og.SuspendUser(user_email):
        logging.info(f"{user_email} was suspended")
    else:
        logging.warn(f"Could not suspend {user_email}")