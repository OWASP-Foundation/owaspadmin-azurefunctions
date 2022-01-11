import logging

import azure.functions as func
import csv
import json
import base64
from io import StringIO

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    filej = req.params.get('file')
    if not filej:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            filej = req_body.get('file')

    if filej:
        f64part = filej[filej.find('base64,') + 7:]
        fstr = base64.b64decode(f64part).decode(encoding='utf-8')
        logging.info("opening reader")
        file = StringIO(fstr)
        csvreader = reader = csv.DictReader(file)
        email = 'No Email'
        for row in csvreader:
            logging.info(row)
            email = row['Email']
            logging.info(f"Processing row for {email}")

        logging.info('done with reader')
        return func.HttpResponse("Got the file.")
    else:
        logging.error("failed to get file from post")
        return func.HttpResponse(
             "Something is not right.",
             status_code=400
        )
