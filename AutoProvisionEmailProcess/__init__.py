import logging

from azure.functions import QueueMessage


def main(msg: QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    logging.info(f"Would have provisioned an email for {msg.get_body().decode('utf-8')}")