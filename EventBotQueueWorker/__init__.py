import logging

import azure.functions as func

import os
import json
import requests
import time

from ..SharedCode.eventbot.slack_response import SlackResponse
from ..SharedCode.eventbot.event import Event
from ..SharedCode.eventbot.product import Product
from ..SharedCode.eventbot.discount_code import DiscountCode

def main(msg: func.QueueMessage) -> None:
    payload = json.loads(msg.get_body().decode('utf-8'))

    event_type = payload.get('event_type', None)
    event_payload = payload.get('payload', {})
    response_url = payload.get('response_url', None)

    if event_type == 'create_event':
        Event.create_event(event_payload, response_url)
    elif event_type == 'list_events':
        Event.list_events(response_url)
    elif event_type == 'create_product':
        Product.create_product(event_payload, response_url)
    elif event_type == 'update_product':
        Product.edit_product(event_payload, response_url)
    elif event_type == 'create_discount_code':
        DiscountCode.create(event_payload, response_url)
    elif event_type == 'create_discount_code':
        DiscountCode.create(event_payload, response_url)
    elif event_type == 'change_product_position':
        Product.change_position(event_payload, response_url)
