import logging
import json
from azure.functions import QueueMessage


def main(msg: QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    users = json.loads(msg.get_body().decode('utf-8'))

    for user in users:
        logging.info(f"Would have provisioned an email for {user.get('email')}")