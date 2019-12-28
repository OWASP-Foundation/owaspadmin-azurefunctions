import logging

import azure.functions as func

import os
import json
import pathlib
from typing import Dict

import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]

def main(req: func.HttpRequest) -> func.HttpResponse:
    request = req.get_json()

    checkout_session = request.get('token', None)

    if checkout_session is None:
        errors = {
            'token': ['token is required']
        }
        return return_response(errors, False)
    else:
        cancel_membership(checkout_session)
        return return_response({}, True)


def cancel_membership(checkout_session):
    session = stripe.checkout.Session.retrieve(checkout_session)
    setup_intent = session.get('setup_intent', None)
    if setup_intent is not None:
        setup_intent = stripe.SetupIntent.retrieve(setup_intent)
        metadata = setup_intent.get('metadata', {})
        subscription_id = metadata.get('subscription_id', None)
        customer_id = metadata.get('customer_id', None)
        if subscription_id is not None:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            stripe.Customer.modify(
                customer_id,
                metadata={
                    "membership_recurring": "no"
                }
            )



def return_response(response, success):
    if success:
        status_code = 200
        response = {
            "status": "OK",
            "data": response
        }
    else:
        status_code = 400
        response = {
            "status": "ERROR",
            "errors": response
        }

    return func.HttpResponse(
        body=json.dumps(response),
        status_code=status_code
    )
