import datetime
import logging
import os
from urllib.parse import unquote_plus
import json
import base64
import azure.functions as func
from azure.storage.queue import QueueClient, QueueMessage

from ..SharedCode import salesforce
from ..SharedCode import wufoo


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    # TODO replicate steps from zapier:
    # if paid, do the following:
    # Find or Create Salesforce Account based on University
    # Find or Create Contact in Salesforce based on email
    # Create Badge in Salesforce
    # Create Subscription in Salesforce
    # Consideration: Create Sales Item and Sales Line Item, etc as needed

    if mytimer.past_due:
        logging.info('The timer is past due!')

    #queue_service = QueueServiceClient.from_connection_string(os.environ["owaspadmin941c_STORAGE"])
    queue = QueueClient.from_connection_string(os.environ['owaspadmin941c_STORAGE'], 'student-membership-queue')
    messages = queue.receive_messages()
    wf = wufoo.OWASPWufoo()
    sf = salesforce.OWASPSalesforce()
    sf.Login()

    for message in messages:
        content = base64.b64decode(message.content)
        strbody = unquote_plus(content.decode('utf-8'))
        names = dict(x.split('=') for x in strbody.split('&'))
        email = names[wf.EMAIL_FIELD]
        firstname = names[wf.FIRST_NAME_FIELD]
        lastname = names[wf.LAST_NAME_FIELD]
        university = names[wf.UNIVERSITY_FIELD]
        datecreated = names[wf.DATE_CREATED_FIELD]
        transaction_id = names[wf.TRANSACTION_FIELD]
        merchant_type = names[wf.MERCHANT_TYPE_FIELD]
        status = wf.GetPaidField(os.environ['WF_STUDENT_FORM'], email, datecreated)
        if 'Paid' in status:
            if sf.GenerateStudentSubscription(firstname, lastname, email, university, transaction_id, merchant_type):
               queue.delete_message(message.id, message.pop_receipt)
            
    logging.info('Python timer trigger function ran at %s', utc_timestamp)
