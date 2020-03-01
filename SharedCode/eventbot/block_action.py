import os
import json
import requests
import logging
import azure.functions as func
from .slack_response import SlackResponse
from .event import Event
from .product import Product
from .discount_code import DiscountCode


class BlockAction:
    payload = None
    trigger_id = None
    response_url = None
    action_value = None
    action_id = None
    block_id = None

    def __init__(self, payload={}):
        self.payload = payload
        self.response_url = payload.get('response_url', None)
        self.trigger_id = payload.get('trigger_id', None)
        actions = payload.get('actions', [])

        if actions[0].get('selected_option', None) is not None:
            self.action_value = actions[0]['selected_option']['value']
        else:
            self.action_value = actions[0]['value']

        self.action_id = actions[0].get('action_id', None)
        self.block_id = actions[0].get('block_id', None)


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
        elif self.action_id == 'create_discount_code':
            DiscountCode.show_create_form(self.trigger_id, self.response_url, self.action_value)
        elif self.action_id == 'list_discount_codes':
            DiscountCode.list(self.trigger_id, self.response_url, self.action_value)
        elif self.action_id == 'manage_product' and self.action_value == 'delete':
            product_id = self.block_id.partition('|')[2]
            Product.edit(self.trigger_id, self.response_url, product_id)

        acknowledgement = SlackResponse.acknowledgement()
        return acknowledgement.send()

