import logging
import json
import azure.functions as func
from datetime import datetime
from ..SharedCode import helperfuncs
import stripe
import os

stripe.api_key = os.environ["STRIPE_SECRET"]


def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    data = json.loads(msg.get_body().decode('utf-8'))
    user_email = data.get('email', None)
    customer_id = data.get('customer_id', None)
    notification_sent = helperfuncs.send_notification(user_email, 7)
    if notification_sent:
        stripe.Customer.modify(customer_id, metadata={
            "membership_notified": "true"},)
        stripe.Customer.modify(customer_id, metadata={
            "membership_notified_date": datetime.utcnow().strftime('%Y-%m-%d')},)
        stripe.Customer.modify(customer_id, metadata={
            "membership_last_notification": '7 day'},)
    else:
        logging.warn(user_email + '- 7 day notification could not be sent' + "\n")