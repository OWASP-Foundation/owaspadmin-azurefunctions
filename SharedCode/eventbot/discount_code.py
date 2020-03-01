import re
import os
import logging
import json
import stripe

from .event import Event
from .slack_response import SlackResponse

class DiscountCode:
    def create(event_payload={}, response_url=None):
        product = stripe.Product.retrieve(
            event_payload.get('event_id'),
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )

        metadata = {
            'event_id': event_payload.get('event_id')
        }

        new_discount_code = stripe.Coupon.create(
            duration='forever',
            amount_off=event_payload.get('amount_off'),
            currency=product['metadata']['currency'],
            id=re.sub('[^A-Za-z0-9]+', '', event_payload.get('code').upper()),
            metadata=metadata,
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )

        response_message = SlackResponse.message(response_url, 'Discount code created successfully')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: * Discount code created successfully!*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "The discount code *" + new_discount_code["id"] + "* has been successfully created.\n\nYou may use the buttons below to continue making changes to the event named *" + product["name"] + "*."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(Event.get_event_actions_blocks(product["id"]))
        response_message.send()


    def show_create_form(trigger_id=None, response_url=None, event_id=None):
        modal_response = SlackResponse.modal(
            callback_id='create_discount_code|' + event_id,
            title='Create Discount Code',
            submit_label='Create',
            close_label='Cancel',
            trigger_id=trigger_id,
            response_url=response_url
        )
        modal_response.add_block({
            "type": "input",
            "block_id": "discount_code_code",
            "element": {
                "type": "plain_text_input",
                "action_id": "discount_code_code_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter a unique code"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Code"
            },
            "hint": {
                "type": "plain_text",
                "text": "This code must be unique and include alphanumeric characters only."
            }
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "discount_code_amount_off",
            "element": {
                "type": "plain_text_input",
                "action_id": "discount_code_amount_off_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "0"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Amount Off Regular Price"
            },
            "hint": {
                "type": "plain_text",
                "text": "Enter a whole number. Do not include a currency sign or commas."
            }
        })
        modal_response.send()


    def list(trigger_id, response_url, event_id):
        response_message = SlackResponse.message(response_url, 'Discount Code Listing')

        discount_codes = []

        stripe_coupons = stripe.Coupon.list(
            limit=50,
            api_key=os.environ["STRIPE_TEST_SECRET"]
        )
        for stripe_coupon in stripe_coupons.auto_paging_iter():
            metadata = stripe_coupon.get('metadata', {})
            if metadata.get('event_id', None) == event_id:
                discount_codes.append({
                    "id": stripe_coupon["id"],
                    "amount_off": str(stripe_coupon['amount_off'] / 100) + '0'
                })

        if len(discount_codes):
            response_message.add_block({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Discount Code Listing*"
                }
            })
            response_message.add_block({
                "type": "divider"
            })

            product = stripe.Product.retrieve(
                event_id,
                api_key=os.environ["STRIPE_TEST_SECRET"]
            )

            currency = product['metadata'].get('currency', 'usd')
            if currency == 'eur':
                currency_symbol = '€'
            elif currency == 'gbp':
                currency_symbol = '£'
            else:
                currency_symbol = '$'

            for discount_code in discount_codes:
                response_message.add_block({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*" + discount_code["id"] + "* (" + currency_symbol + discount_code['amount_off'] + " off)"
                    }
                })
        else:
            response_message.add_error_response_blocks('No discount codes found for this event.')

        response_message.add_block(Event.get_event_actions_blocks(event_id))
        response_message.send()


    def handle_create_submission(input_values, queue, response_url=None, event_id=None):
        queue_data = {
            'event_type': 'create_discount_code',
            'payload': {}
        }

        if event_id is not None:
            queue_data["payload"]["event_id"] = event_id

        if response_url is not None:
            queue_data['response_url'] = response_url

        for input_field in input_values:
            if input_field['input_id'] == 'discount_code_amount_off_input':
                queue_data["payload"]["amount_off"] = int(float(input_field["value"]) * 100)
            elif input_field['input_id'] == 'discount_code_code_input':
                queue_data['payload']['code'] = input_field['value']

        queue.set(json.dumps(queue_data))
