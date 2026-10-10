import logging
import json
import azure.functions as func
from datetime import datetime, timezone
import SharedCode.helperfuncs as helperfuncs
from SharedCode.azure_tables import get_email_notify_table_client
from azure.data.tables import UpdateMode

def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    
    data = json.loads(msg.get_body().decode('utf-8'))
    user_email = data.get('email', None)
    # do not notify during testing...
    #notification_sent = helperfuncs.send_notification(user_email, 15)
    notification_sent = True    
    if notification_sent:
        table_client = get_email_notify_table_client()
        email_entry = {
            'PartitionKey':'email_notify',
            'RowKey': user_email,
            'LastNotification': datetime.now(timezone.utc).isoformat(),
        }        
        table_client.upsert_entity(email_entry, mode=UpdateMode.REPLACE)
        logging.info(f"Updated {user_email} to next notification date")
    else:
        logging.warning(user_email + '- 15 day notification could not be sent' + "\n")
