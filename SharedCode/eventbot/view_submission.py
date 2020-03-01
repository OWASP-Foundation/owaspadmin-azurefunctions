import os
import json
import requests
import logging
import azure.functions as func
from .slack_response import SlackResponse
from .event import Event
from .product import Product
from .discount_code import DiscountCode


class ViewSubmission:
    payload = None
    callback_id = None
    callback_params = None
    trigger_id = None
    response_url = None
    input_values = []

    def __init__(self, payload={}):
        self.payload = payload
        self.input_values = []
        view = payload.get('view', {})
        state = view.get('state', {})
        self.trigger_id = payload.get('trigger_id', None)

        callback_id = view.get('callback_id', None)
        if callback_id is None or '|' not in callback_id:
            self.callback_id = callback_id
        else:
            (action_name, action_payload) = callback_id.split("|",1)
            self.callback_id = action_name
            self.callback_params = action_payload

        self.response_url = view.get('private_metadata')
        input_blocks = state.get('values', {})

        for key in input_blocks:
            for form_field in input_blocks[key]:
                field_dict = input_blocks[key][form_field]
                if field_dict.get('type', 'plain_text_input') == 'static_select':
                    field_value = field_dict['selected_option']['value']
                elif field_dict.get('type', 'plain_text_input') == 'datepicker':
                    field_value = field_dict.get('selected_date', None)
                else:
                    field_value = field_dict.get('value', None)
                self.input_values.append({
                    'block_id': key,
                    'input_id': form_field,
                    'value': field_value,
                })


    def process(self, queue):
        try:
            if self.callback_id == 'create_event':
                Event.handle_create_submission(
                    self.input_values,
                    queue=queue,
                    response_url=self.response_url
                )
            if self.callback_id == 'create_product':
                Product.handle_create_submission(
                    self.input_values,
                    queue=queue,
                    response_url=self.response_url,
                    event_id=self.callback_params
                )
            if self.callback_id == 'create_discount_code':
                DiscountCode.handle_create_submission(
                    self.input_values,
                    queue=queue,
                    response_url=self.response_url,
                    event_id=self.callback_params
                )
            if self.callback_id == 'edit_product':
                Product.handle_edit_submission(
                    self.input_values,
                    queue=queue,
                    response_url=self.response_url,
                    product_id=self.callback_params
                )
        except Exception as excptn:
            response = {
                "response_action": "errors",
                "errors": excptn.args[0]
            }
            return func.HttpResponse(
                body=json.dumps(response),
                headers={
                    "Content-type": "application/json"
                },
                status_code=200
            )

        response = {
            "response_action": "clear"    
        }

        return func.HttpResponse(
            body=json.dumps(response),
            headers={
                "Content-type": "application/json"
            },
            status_code=200
        )
