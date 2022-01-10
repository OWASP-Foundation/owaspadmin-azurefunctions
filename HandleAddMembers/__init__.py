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
        csvreader = reader = csv.DictReader(file)
        email = 'No Email'
        for row in csvreader:
            email = row['Email']

        return func.HttpResponse(f"Got the file and the first email is {email}.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
