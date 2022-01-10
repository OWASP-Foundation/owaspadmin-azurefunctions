import logging

import azure.functions as func
import csv

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    file = req.params.get('file')
    if not file:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            file = req_body.get('file')

    if file:
        logging.info("opening reader")
        csvreader = reader = csv.DictReader(file)
        email = 'No Email'
        for row in csvreader:
            logging.info(row)
            #email = row['Email']
            #logging.info(f"Processing row for {email}")

        logging.info('done with reader')
        return func.HttpResponse("Got the file.")
    else:
        logging.error("failed to get file from post")
        return func.HttpResponse(
             "Something is not right.",
             status_code=400
        )
