import os
import json
import requests
import logging
import azure.functions as func
from .slack_response import SlackResponse
from .event import Event
from .product import Product


class BlockAction:
    payload = None
    trigger_id = None
    response_url = None
    action_value = None
    action_id = None

    def __init__(self, payload={}):
        self.payload = payload
        self.response_url = payload.get('response_url', None)
        self.trigger_id = payload.get('trigger_id', None)
        actions = payload.get('actions', [])

        self.action_value = actions[0]['value']
        self.action_id = actions[0].get('action_id', None)


    def process(self, queue):
        if self.action_id == 'create_event':
            Event.show_create_form(self.trigger_id, self.response_url)
        elif self.action_id == 'list_events':
            Event.list_events(self.response_url)
        elif self.action_id == 'manage_event':
            Event.show_event(self.response_url, self.action_value)
        elif self.action_id == 'add_product':
            Product.show_create_form(self.trigger_id, self.response_url, self.action_value)
        elif self.action_id == 'list_products':
            Product.list_products(self.trigger_id, self.response_url, self.action_value)

        acknowledgement = SlackResponse.acknowledgement()
        return acknowledgement.send()

