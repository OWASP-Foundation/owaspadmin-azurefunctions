import logging
import json
import azure.functions as func
from datetime import datetime
from ..SharedCode import helperfuncs
from ..SharedCode import googleapi
from ..SharedCode.azure_tables import get_email_notify_table_client



def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    data = json.loads(msg.get_body().decode('utf-8'))
    user_email = data.get('email', None)    
    og = googleapi.OWASPGoogle()
    logging.info(f"Would have suspended user {user_email} at {datetime.now()}")
    # not disabling users at this point, only verifying that the flow works.
    # if og.SuspendUser(user_email):
    #     logging.info(f"{user_email} was suspended")
    #     table_client = get_email_notify_table_client()
    #     table_client.delete_entity("email_notify", user_email)
    # else:
    #     logging.warn(f"Could not suspend {user_email}")