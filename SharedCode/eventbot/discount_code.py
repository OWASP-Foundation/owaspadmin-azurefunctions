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
            api_key=os.environ["STRIPE_SECRET"]
        )

        metadata = {
            'event_id': event_payload.get('event_id')
        }

        if event_payload.get('inventory', None) is not None:
            metadata['inventory'] = event_payload.get('inventory')

        if event_payload.get('amount_off', None) is not None:
            new_discount_code = stripe.Coupon.create(
                duration='forever',
                amount_off=event_payload.get('amount_off'),
                currency=product['metadata']['currency'],
                id=re.sub('[^A-Za-z0-9]+', '', event_payload.get('code').upper()),
                metadata=metadata,
                api_key=os.environ["STRIPE_SECRET"]
            )
        else:
            new_discount_code = stripe.Coupon.create(
                duration='forever',
                percent_off=event_payload.get('percent_off'),
                currency=product['metadata']['currency'],
                id=re.sub('[^A-Za-z0-9]+', '', event_payload.get('code').upper()),
                metadata=metadata,
                api_key=os.environ["STRIPE_SECRET"]
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


    def show_create_form(trigger_id=None, response_url=None, event_id=None, discount_code={}, mode='create'):
        if mode == 'update':
            callback_id = 'edit_discount_code|' + discount_code["id"]
            submit_label = 'Update'
            title = 'Edit Discount Code'
            product = stripe.Product.retrieve(
                discount_code['metadata'].get('event_id'),
                api_key=os.environ["STRIPE_SECRET"]
            )
            currency = product['metadata'].get('currency', 'usd')
            if currency == 'eur':
                currency_symbol = '€'
            elif currency == 'gbp':
                currency_symbol = '£'
            else:
                currency_symbol = '$'
        else:
            callback_id = 'create_discount_code|' + event_id
            submit_label = 'Create'
            title = 'Create Discount Code'

        modal_response = SlackResponse.modal(
            callback_id=callback_id,
            title=title,
            submit_label=submit_label,
            close_label='Cancel',
            trigger_id=trigger_id,
            response_url=response_url
        )
        if mode == 'create':
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
        else:
            modal_response.add_block({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Code:* " + discount_code.get('id', '')
                }
            })
        if mode == 'create':
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
                    "text": "Enter a whole number. Do not include a currency sign or commas. This field is optional for comp discount codes."
                },
                "optional": True
            })
        else:
            if (discount_code.get('amount_off')):
                amount_off = currency_symbol + str(discount_code.get('amount_off') / 100) + '0' + ' off'
            else:
                amount_off = str(discount_code.get('percent_off')) + "% off"
            modal_response.add_block({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Amount off:* " + amount_off
                }
            })
        if mode == 'update' and discount_code.get('metadata', {}).get('inventory', None) is not None:
            modal_response.add_block({
                "type": "input",
                "block_id": "discount_code_inventory",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "discount_code_inventory_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Remaining Redemptions"
                    },
                    "initial_value": discount_code['metadata']['inventory']
                },
                "label": {
                    "type": "plain_text",
                    "text": "Remaining Redemptions"
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Optional. The number of times this discount code can be used. Leave blank for unlimited redemptions."
                },
                "optional": True
            })
        else:
            modal_response.add_block({
                "type": "input",
                "block_id": "discount_code_inventory",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "discount_code_inventory_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Available Redemptions"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Available Redemptions"
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Optional. The number of times this discount code can be used. Leave blank for unlimited redemptions."
                },
                "optional": True
            })
        if mode == 'create':
            modal_response.add_block({
                "type": "input",
                "block_id": "discount_code_comp",
                "element": {
                    "type": "checkboxes",
                    "action_id": "discount_code_comp_input",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "This is a comp (100% off) discount code"
                            },
                            "value": "comp"
                        }
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Comp Settings"
                },
                "optional": True
            })
        modal_response.send()


    def list(trigger_id, response_url, event_id):
        response_message = SlackResponse.message(response_url, 'Discount Code Listing')

        discount_codes = []

        stripe_coupons = stripe.Coupon.list(
            limit=50,
            api_key=os.environ["STRIPE_SECRET"]
        )
        for stripe_coupon in stripe_coupons.auto_paging_iter():
            metadata = stripe_coupon.get('metadata', {})
            if metadata.get('event_id', None) == event_id:
                if stripe_coupon.get('amount_off', None) is not None:
                    discount_codes.append({
                        "id": stripe_coupon["id"],
                        "amount_off": str(stripe_coupon['amount_off'] / 100) + '0',
                        "inventory": metadata.get('inventory', None)
                    })
                else:
                    discount_codes.append({
                        "id": stripe_coupon["id"],
                        "percent_off": int(stripe_coupon['percent_off']),
                        "inventory": metadata.get('inventory', None)
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
                api_key=os.environ["STRIPE_SECRET"]
            )

            currency = product['metadata'].get('currency', 'usd')
            if currency == 'eur':
                currency_symbol = '€'
            elif currency == 'gbp':
                currency_symbol = '£'
            else:
                currency_symbol = '$'

            for discount_code in discount_codes:
                if discount_code.get('amount_off', None):
                    amount_off = currency_symbol + discount_code['amount_off']
                else:
                    amount_off = str(discount_code['percent_off']) + "%"
                response_message.add_block({
                    "type": "section",
                    "block_id": "manage_discount_code|" + discount_code["id"],
                    "text": {
                        "type": "mrkdwn",
                        "text": "*" + discount_code["id"] + "* (" + amount_off + " off)" + ((' ' + discount_code['inventory'] + ' Redemptions remaining') if discount_code['inventory'] is not None else '')
                    },
                    "accessory": {
                        "type": "overflow",
                        "action_id": "manage_discount_code",
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Edit Discount Code"
                                },
                                "value": "edit"
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Delete Discount Code"
                                },
                                "value": "delete"
                            }
                        ]
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
            if input_field['input_id'] == 'discount_code_amount_off_input' and input_field.get('value', None) is not None:
                queue_data["payload"]["amount_off"] = int(float(input_field["value"]) * 100)
            elif input_field['input_id'] == 'discount_code_code_input':
                queue_data['payload']['code'] = input_field['value']
            elif input_field['input_id'] == 'discount_code_inventory_input' and input_field.get('value', '') != '':
                queue_data['payload']['inventory'] = input_field['value']
            elif input_field['input_id'] == 'discount_code_comp_input' and input_field.get('value', '') != '':
                queue_data['payload']['percent_off'] = 100

        queue.set(json.dumps(queue_data))


    def delete(input_values, queue, response_url=None, discount_code=None):
        discount_code = stripe.Coupon.retrieve(
            discount_code,
            api_key=os.environ["STRIPE_SECRET"]
        )
        product = stripe.Product.retrieve(
            discount_code['metadata']['event_id'],
            api_key=os.environ["STRIPE_SECRET"]
        )
        stripe.Coupon.delete(
            discount_code['id'],
            api_key=os.environ["STRIPE_SECRET"]
        )
        response_message = SlackResponse.message(response_url, 'Discount Code deleted successfully')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: * Discount Code deleted successfully!*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*" + discount_code['id'] + "* has been successfully deleted.\n\nYou may use the buttons below to continue making changes to the event named " + product['name'] + "."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(Event.get_event_actions_blocks(product['id']))
        response_message.send()


    @classmethod
    def edit(cls, trigger_id, response_url, discount_code_id):
        discount_code = stripe.Coupon.retrieve(
            discount_code_id,
            api_key=os.environ["STRIPE_SECRET"]
        )
        cls.show_create_form(
            trigger_id=trigger_id,
            response_url=response_url,
            discount_code=discount_code,
            mode='update'
        )


    def confirm_delete(trigger_id, response_url, discount_code_id):
        modal_response = SlackResponse.modal(
            callback_id='delete_discount_code|' + discount_code_id,
            title='Delete Discount Code?',
            submit_label='Delete',
            close_label='Cancel',
            trigger_id=trigger_id,
            response_url=response_url
        )
        modal_response.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Are you sure you want to delete this discount code? This operation cannot be undone."
            }
        })
        modal_response.send()
