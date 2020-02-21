import os
import logging
import json

from .slack_response import SlackResponse
from .event import Event

import stripe

class Product:
    def create_product(event_payload={}, response_url=None):
        product = stripe.Product.retrieve(
            event_payload.get('event_id'),
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )

        metadata = {
            "type": "regular"
        }

        if event_payload.get('display_start', None) is not None:
            metadata["display_start"] = event_payload["display_start"]
        if event_payload.get('display_end', None) is not None:
            metadata["display_end"] = event_payload["display_end"]
        if event_payload.get('inventory', None) is not None and event_payload.get('inventory') != 0:
            metadata["inventory"] = event_payload["inventory"]
            metadata["starting_inventory"] = event_payload["inventory"]
        if event_payload.get('description', None) is not None:
            metadata["description"] = event_payload["description"]

        sku = stripe.SKU.create(
            attributes={
                "name": event_payload.get('name')
            },
            price=event_payload.get('amount'),
            currency=product["metadata"].get('currency', 'usd'),
            inventory={"type": "infinite"},
            product=product["id"],
            metadata=metadata,
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )

        response_message = SlackResponse.message(response_url, 'Product created successfully')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: * Product created successfully!*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*" + sku["attributes"]["name"] + "* has been successfully created.\n\nYou may use the buttons below to continue making changes to the event named " + product["name"] + "."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(Event.get_event_actions_blocks(product["id"]))
        response_message.send()


    def list_products(trigger_id, response_url, event_id):
        response_message = SlackResponse.message(response_url, 'Product Listing')
        product_list = stripe.SKU.list(
            product=event_id,
            limit=20,
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )

        if len(product_list):
            response_message.add_block({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Product Listing*"
                }
            })
            response_message.add_block({
                "type": "divider"
            })
            for product in product_list:
                response_message.add_block({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": product["attributes"]["name"]
                    }
                })
        else:
            response_message.add_block({
                "type": "section",
                "text": {
                        "type": "mrkdwn",
                        "text": ":exclamation: *Error*\nNo products found."
                }
            })
            response_message.add_block({
                "type": "divider"
            })

        response_message.add_block(Event.get_event_actions_blocks(event_id))
        response_message.send()


    def show_create_form(trigger_id=None, response_url=None, event_id=None, mode='create'):
        if mode == 'update':
            pass
        else:
            callback_id = 'create_product|' + event_id
            submit_label = 'Create'
            title = 'Create Product'

        modal_response = SlackResponse.modal(
            callback_id=callback_id,
            title=title,
            submit_label=submit_label,
            close_label='Cancel',
            trigger_id=trigger_id,
            response_url=response_url
        )
        modal_response.add_block({
            "type": "input",
            "block_id": "product_name",
            "element": {
                "type": "plain_text_input",
                "action_id": "product_name_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter the name of the product"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Product Name"
            }
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "product_description",
            "element": {
                "type": "plain_text_input",
                "action_id": "product_description_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter a description for this product"
                },
                "multiline": True,
                "max_length": 500
            },
            "label": {
                "type": "plain_text",
                "text": "Product Description"
            },
            "hint": {
                "type": "plain_text",
                "text": "This description will be displayed next to the product name on the registration page. Markdown formatting is allowed."
            }
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "product_amount",
            "element": {
                "type": "plain_text_input",
                "action_id": "product_amount_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "0.00"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Product Price"
            },
            "hint": {
                "type": "plain_text",
                "text": "Enter a whole number or decimal number. Do not include a currency sign or commas."
            }
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "product_inventory_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "product_inventory_input"
            },
            "label": {
                "type": "plain_text",
                "text": "Product Inventory"
            },
            "hint": {
                "type": "plain_text",
                "text": "Optional. Leave blank to sell an unlimited amount."
            },
            "optional": True
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "product_display_start_input",
            "element": {
                "type": "datepicker",
                "action_id": "product_display_start_input",
            },
            "label": {
                "type": "plain_text",
                "text": "Begin Display"
            },
            "optional": True
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "product_display_end_input",
            "element": {
                "type": "datepicker",
                "action_id": "product_display_end_input",
            },
            "label": {
                "type": "plain_text",
                "text": "End Display"
            },
            "optional": True
        })
        modal_response.send()


    def handle_create_submission(input_values, queue, response_url=None, event_id=None):
        errors = {}

        for input_value in input_values:
            if input_value["input_id"] == "product_amount_input":
                form_value = input_value["value"]
                if form_value.isdigit() or (form_value.replace('.','',1).isdigit() and form_value.count('.') < 2):
                    pass
                else:
                    errors[input_value["block_id"]] = "Product amount must be a whole number or decimal"
            if input_value["input_id"] == "product_inventory_input":
                form_value = input_value["value"]
                if form_value is not None and not form_value.isdigit():
                    errors[input_value["block_id"]] = "Product inventory must be a whole number greater than or equal to 0"

        if len(errors):
            raise Exception(errors)

        queue_data = {
            'event_type': 'create_product',
            'payload': {}
        }

        if event_id is not None:
            queue_data["payload"]["event_id"] = event_id

        if response_url is not None:
            queue_data['response_url'] = response_url

        for input_value in input_values:
            if input_value["input_id"] == "product_name_input":
                queue_data["payload"]["name"] = input_value["value"]
            if input_value["input_id"] == "product_description_input":
                queue_data["payload"]["description"] = input_value["value"]
            elif input_value["input_id"] == "product_amount_input":
                queue_data["payload"]["amount"] = int(float(input_value["value"]) * 100)
            elif input_value["input_id"] == "product_inventory_input" and input_value["value"] is not None:
                queue_data["payload"]["inventory"] = input_value["value"]
            elif input_value["input_id"] == "product_display_start_input" and input_value["value"] is not None:
                queue_data["payload"]["display_start"] = input_value["value"]
            elif input_value["input_id"] == "product_display_end_input" and input_value["value"] is not None:
                queue_data["payload"]["display_end"] = input_value["value"]

        queue.set(json.dumps(queue_data))
