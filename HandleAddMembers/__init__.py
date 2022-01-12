import logging

import azure.functions as func
import base64

def main(req: func.HttpRequest, mqueue: func.Out[func.QueueMessage]) -> func.HttpResponse:
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
        #need to put this on queue and let queue do the work...takes too long to respond to user
        fstr = base64.b64decode(f64part).decode(encoding='utf-8')
        mqueue.set(fstr)
        return func.HttpResponse("File received.")
    else:
        logging.error("failed to get file from post")
        return func.HttpResponse(
             "Something is not right.",
             status_code=400
        )

