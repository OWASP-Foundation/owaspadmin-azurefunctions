import logging
import json
from azure.functions import QueueMessage


def main(msg: QueueMessage) -> None:
    
    user = json.loads(msg.get_body().decode('utf-8'))
    logging.info(f"Would have provisioned an email for {user.get('email')}")