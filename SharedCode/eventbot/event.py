import os
import logging
import json

from .slack_response import SlackResponse

import stripe
stripe.api_key = os.environ["STRIPE_TEST_SECRET"]

class Event:
    @classmethod
    def create_event(cls, payload, response_url=None):
        product = stripe.Product.create(
            name=payload.get('name'),
            attributes=['name'],
            description=payload.get('name'),
            type="good",
            metadata={
                "repo_name": payload.get('repo_name'),
                "type": "event",
                "currency": payload.get('currency')
            }
        )

        response_message = SlackResponse.message(response_url, 'Event created successfully')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: *Event created successfully!*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": product['name'] + " has been successfully created. Use the buttons below to manage this event."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(cls.get_event_actions_blocks(product["id"]))
        response_message.send()


    def handle_create_submission(input_values, queue, response_url=None):
        event_data = {
            'event_type': 'create_event',
            'payload': {
                'currency': 'usd',
                'name': '',
                'repo_name': ''
            }
        }

        if response_url is not None:
            event_data['response_url'] = response_url

        for input_field in input_values:
            if input_field['input_id'] == 'event_currency_input':
                event_data['payload']['currency'] = input_field['value']
            elif input_field['input_id'] == 'event_name_input':
                event_data['payload']['name'] = input_field['value']
            elif input_field['input_id'] == 'event_repository_input':
                event_data['payload']['repo_name'] = input_field['value']

        queue.set(json.dumps(event_data))


    def all_options(response_url=None):
        response_message = SlackResponse.message(response_url, 'Event Bot Options')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Event Bot Options*\nWelcome to the event bot. You can use the buttons below to manage events. To view and update products associated with an event, first list all events and select the event from the listing."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "actions",
            "block_id": "event_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Create Event"
                    },
                    "value": "create_event",
                    "action_id": "create_event"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "List Events"
                    },
                    "value": "list_events",
                    "action_id": "list_events"
                }
            ]
        })
        response_message.send()


    def list_events(response_url):
        event_list = []
        stripe_products = stripe.Product.list(limit=10)
        for event in stripe_products:
            metadata = event.get('metadata', {})
            product_type = metadata.get('type', None)

            if product_type == 'event':
                event_list.append({
                    'name': event.name,
                    'id': event.id
                })

        response_message = SlackResponse.message(response_url=response_url, text='Event Listing')

        if len(event_list):
            response_message.add_block({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Event Listing*"
                }
            })
            response_message.add_block({
                "type": "divider"
            })
            for event in event_list:
                response_message.add_block({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": event['name']
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Manage",
                            "emoji": True
                        },
                        "value": event["id"],
                        "action_id": "manage_event"
                    }
                })
        else:
            response_message.add_block({
                "type": "section",
                "text": {
                        "type": "mrkdwn",
                        "text": ":exclamation: *Error*\nNo events found."
                }
            })
            response_message.add_block({
                "type": "divider"
            })

        response_message.add_block({
            "type": "actions",
            "block_id": "event_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Create Event"
                    },
                    "value": "create_event",
                    "action_id": "create_event"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "List Events"
                    },
                    "value": "list_events",
                    "action_id": "list_events"
                }
            ]
        })

        response_message.send()


    @classmethod
    def show_event(cls, response_url, product_id):
        product = stripe.Product.retrieve(product_id)
        response_message = SlackResponse.message(response_url, text='Manage Event')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Manage Event*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Use the buttons below to manage the event named *" + product["name"] + "*."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(cls.get_event_actions_blocks(product["id"]))
        response_message.send()


    def show_create_form(trigger_id=None, response_url=None):
        modal_response = SlackResponse.modal(
            callback_id='create_event',
            title='Create Event',
            submit_label='Create',
            close_label='Cancel',
            trigger_id=trigger_id,
            response_url=response_url
        )
        modal_response.add_block({
            "type": "input",
            "block_id": "event_name",
            "element": {
                "type": "plain_text_input",
                "action_id": "event_name_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter the name of the event"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Event Name"
            }
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "event_repository",
            "element": {
                "type": "plain_text_input",
                "action_id": "event_repository_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter the name of the repository"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Event Repository"
            }
        })
        modal_response.add_block({
            "type": "input",
            "block_id": "event_currency",
            "element": {
                "type": "static_select",
                "action_id": "event_currency_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select the billing currency"
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "USD"
                    },
                    "value": "usd"
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "USD"
                        },
                        "value": "usd"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "EUR"
                        },
                        "value": "eur"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "GBP"
                        },
                        "value": "gbp"
                    }
                ]
            },
            "label": {
                "type": "plain_text",
                "text": "Billing Currency"
            }
        })
        modal_response.send()


    def get_event_actions_blocks(event_id):
        actions_block = {
            "type": "actions",
            "block_id": "event_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Add Product"
                    },
                    "value": event_id,
                    "action_id": "add_product"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "List Products"
                    },
                    "value": event_id,
                    "action_id": "list_products"
                }
            ]
        }

        return actions_block
