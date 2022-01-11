import logging

import azure.functions as func
import csv
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    filej = req.params.get('file')
    if not file:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            filej = req_body.get('file')

    if filej:
        logging.info(filej)
        
        file = json.loads(filej)
        logging.info(f"Received file { file.name }")
        logging.info("opening reader")
        csvreader = reader = csv.DictReader(file.read())
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
