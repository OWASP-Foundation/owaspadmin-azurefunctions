import os
import logging
import json

from .slack_response import SlackResponse
from .event import Event

import stripe

class Product:
    @classmethod
    def create_product(cls, event_payload={}, response_url=None):
        product = stripe.Product.retrieve(
            event_payload.get('event_id'),
            api_key=os.environ["STRIPE_SECRET"]
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
        if event_payload.get('description', None) is not None:
            metadata["description"] = event_payload["description"]
        if event_payload.get('discountable', None) is True:
            metadata["discountable"] = event_payload["discountable"]

        metadata["display_order"] = cls.get_new_product_position(event_payload.get('event_id'))

        sku = stripe.SKU.create(
            attributes={
                "name": event_payload.get('name')
            },
            price=event_payload.get('amount'),
            currency=product["metadata"].get('currency', 'usd'),
            inventory={"type": "infinite"},
            product=product["id"],
            metadata=metadata,
            api_key=os.environ["STRIPE_SECRET"]
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


    def edit_product(event_payload={}, response_url=None):
        sku = stripe.SKU.retrieve(
            event_payload.get('product_id'),
            api_key=os.environ["STRIPE_SECRET"]
        )

        metadata = sku.get('metadata', {})

        if event_payload.get('display_start', None) is not None:
            metadata["display_start"] = event_payload["display_start"]
        if event_payload.get('display_end', None) is not None:
            metadata["display_end"] = event_payload["display_end"]
        if event_payload.get('inventory', None) is not None and event_payload.get('inventory') != 0:
            metadata["inventory"] = event_payload["inventory"]
        if event_payload.get('description', None) is not None:
            metadata["description"] = event_payload["description"]

        if event_payload.get('discountable', None) is True:
            metadata["discountable"] = event_payload["discountable"]
        else:
            metadata["discountable"] = False

        sku = stripe.SKU.modify(
            event_payload.get('product_id'),
            attributes={
                "name": event_payload.get('name')
            },
            metadata=metadata,
            api_key=os.environ["STRIPE_SECRET"]
        )

        product = stripe.Product.retrieve(
            sku['product'],
            api_key=os.environ["STRIPE_SECRET"]
        )

        response_message = SlackResponse.message(response_url, 'Product updated successfully')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: * Product updated successfully!*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*" + sku["attributes"]["name"] + "* has been successfully updated.\n\nYou may use the buttons below to continue making changes to the event named " + product["name"] + "."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(Event.get_event_actions_blocks(product["id"]))
        response_message.send()


    @classmethod
    def edit(cls, trigger_id, response_url, product_id):
        product = stripe.SKU.retrieve(
            product_id,
            api_key=os.environ["STRIPE_SECRET"]
        )

        product_metadata = product.get('metadata', {})

        product_payload = {
            'id': product['id'],
            'name': product['attributes']['name'],
            'description': product_metadata.get('description'),
            'amount': int(product['price'] / 100),
            'inventory': product_metadata.get('inventory', ''),
            'display_start': product_metadata.get('display_start', ''),
            'display_end': product_metadata.get('display_end', ''),
            'discountable': product_metadata.get('discountable', False)
        }

        cls.show_create_form(
            trigger_id=trigger_id,
            response_url=response_url,
            mode='update',
            product=product_payload
        )


    def list_products(trigger_id, response_url, event_id):
        response_message = SlackResponse.message(response_url, 'Product Listing')
        product_list = stripe.SKU.list(
            product=event_id,
            limit=100,
            active=True,
            api_key=os.environ["STRIPE_SECRET"]
        )

        if len(product_list):
            product_list = sorted(product_list, key = lambda i: i['metadata'].get('display_order', 0))
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
            inc = 0
            for product in product_list:
                product_options = [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Edit Product"
                        },
                        "value": "edit"
                    }
                ]
                if inc != 0:
                    product_options.append({
                        "text": {
                            "type": "plain_text",
                            "text": "Move Up"
                        },
                        "value": "move_up"
                    })
                if inc != len(product_list) - 1 and len(product_list):
                    product_options.append({
                        "text": {
                            "type": "plain_text",
                            "text": "Move Down"
                        },
                        "value": "move_down"
                    })
                product_options.append({
                    "text": {
                        "type": "plain_text",
                        "text": "Delete Product"
                    },
                    "value": "delete"
                })

                sub_text = product['id']
                if (product['metadata'].get('inventory', None) is not None):
                    sub_text += ' | ' + str(product['metadata']['inventory']) + ' remaining'

                response_message.add_block({
                    "type": "section",
                    "block_id": 'manage_product|' + product["id"],
                    "text": {
                        "type": "mrkdwn",
                        "text": "*" + product["attributes"]["name"] + "*\n" + sub_text
                    },
                    "accessory": {
                        "type": "overflow",
                        "action_id": "manage_product",
                        "options": product_options
                    }
                })
                inc += 1
            response_message.add_block({
                "type": "divider"
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


    def confirm_delete(trigger_id=None, response_url=None, product_id=None):
        modal_response = SlackResponse.modal(
            callback_id='delete_product|' + product_id,
            title='Delete Product?',
            submit_label='Delete',
            close_label='Cancel',
            trigger_id=trigger_id,
            response_url=response_url
        )
        modal_response.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Are you sure you want to delete this product? This operation cannot be undone."
            }
        })
        modal_response.send()


    def show_create_form(
            trigger_id=None,
            response_url=None,
            event_id=None,
            mode='create',
            product={}
    ):
        if mode == 'update':
            callback_id = 'edit_product|' + product["id"]
            submit_label = 'Update'
            title = 'Edit Product'
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
                },
                "initial_value": product.get('name', '')
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
                "max_length": 500,
                "initial_value": product.get('description', '')
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
                },
                "initial_value": str(product.get('amount', ''))
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
                "action_id": "product_inventory_input",
                "initial_value": product.get('inventory', '')
            },
            "label": {
                "type": "plain_text",
                "text": ("Inventory Remaining" if mode == 'update' else "Product Inventory")
            },
            "hint": {
                "type": "plain_text",
                "text": "Optional. Leave blank to sell an unlimited amount."
            },
            "optional": True
        })
        if product.get('discountable', False) == 'True':
            modal_response.add_block({
                "type": "input",
                "block_id": "product_discountable_input",
                "element": {
                    "type": "checkboxes",
                    "action_id": "product_discountable_input",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Discount codes can be applied to this product."
                            },
                            "value": "discountable"
                        }
                    ],
                    "initial_options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Discount codes can be applied to this product."
                            },
                            "value": "discountable"
                        }
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Discount Settings"
                },
                "optional": True
            })
        else:
            modal_response.add_block({
                "type": "input",
                "block_id": "product_discountable_input",
                "element": {
                    "type": "checkboxes",
                    "action_id": "product_discountable_input",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Discount codes can be applied to this product."
                            },
                            "value": "discountable"
                        }
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Discount Settings"
                },
                "optional": True
            })
        if mode == 'create' or product.get('display_start', '') == '':
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
        else:
            modal_response.add_block({
                "type": "input",
                "block_id": "product_display_start_input",
                "element": {
                    "type": "datepicker",
                    "action_id": "product_display_start_input",
                    "initial_date": product.get('display_start', '')
                },
                "label": {
                    "type": "plain_text",
                    "text": "Begin Display"
                },
                "optional": True
            })

        if mode == 'create' or product.get('display_end', '') == '':
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
        else:
            modal_response.add_block({
                "type": "input",
                "block_id": "product_display_end_input",
                "element": {
                    "type": "datepicker",
                    "action_id": "product_display_end_input",
                    "initial_date": product.get('display_end', '')
                },
                "label": {
                    "type": "plain_text",
                    "text": "End Display"
                },
                "optional": True
            })

        modal_response.send()

    
    def delete(input_values, queue, response_url=None, product_id=None):
        sku = stripe.SKU.retrieve(
            product_id,
            api_key=os.environ["STRIPE_SECRET"]
        )
        product = stripe.Product.retrieve(
            sku['product'],
            api_key=os.environ["STRIPE_SECRET"]
        )
        stripe.SKU.modify(
            product_id,
            active=False,
            api_key=os.environ["STRIPE_SECRET"]
        )
        response_message = SlackResponse.message(response_url, 'Product deleted successfully')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: * Product deleted successfully!*"
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*" + sku['attributes']['name'] + "* has been successfully deleted.\n\nYou may use the buttons below to continue making changes to the event named " + product['name'] + "."
            }
        })
        response_message.add_block({
            "type": "divider"
        })
        response_message.add_block(Event.get_event_actions_blocks(product['id']))
        response_message.send()


    def handle_edit_submission(input_values, queue, response_url=None, product_id=None):
        queue_data = {
            'event_type': 'update_product',
            'payload': {}
        }

        if product_id is not None:
            queue_data["payload"]["product_id"] = product_id

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
            elif input_value["input_id"] == "product_discountable_input" and input_value["value"] is not None and input_value["value"] != '':
                queue_data["payload"]["discountable"] = True

        queue.set(json.dumps(queue_data))


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
            elif input_value["input_id"] == "product_description_input":
                queue_data["payload"]["description"] = input_value["value"]
            elif input_value["input_id"] == "product_amount_input":
                queue_data["payload"]["amount"] = int(float(input_value["value"]) * 100)
            elif input_value["input_id"] == "product_inventory_input" and input_value["value"] is not None:
                queue_data["payload"]["inventory"] = input_value["value"]
            elif input_value["input_id"] == "product_display_start_input" and input_value["value"] is not None:
                queue_data["payload"]["display_start"] = input_value["value"]
            elif input_value["input_id"] == "product_display_end_input" and input_value["value"] is not None:
                queue_data["payload"]["display_end"] = input_value["value"]
            elif input_value["input_id"] == "product_discountable_input" and input_value["value"] is not None and input_value["value"] != '':
                queue_data["payload"]["discountable"] = True

        queue.set(json.dumps(queue_data))


    def get_new_product_position(event_id):
        products = stripe.SKU.list(
            active=True,
            product=event_id,
            limit=100,
            api_key=os.environ["STRIPE_SECRET"]
        )
        
        max_position = 1

        for product in products:
            product_metadata = product.get('metadata', {})
            display_position = int(product_metadata.get('display_order', 0))
            if display_position >= max_position:
                max_position = display_position + 1

        return max_position


    @classmethod
    def change_position(cls, payload, response_url):
        response_message = SlackResponse.message(response_url, 'Product Listing')
        response_message.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Sit tight, the product listing is being reordered..."
            }
        })
        response_message.send()

        product_id = payload['product_id']
        direction = payload['direction']

        sku = stripe.SKU.retrieve(
            product_id,
            api_key=os.environ["STRIPE_SECRET"]
        )

        all_skus = stripe.SKU.list(
            active=True,
            product=sku.get('product'),
            limit=100,
            api_key=os.environ["STRIPE_SECRET"]
        )

        sku_metadata = sku.get('metadata', {})
        current_position = int(sku_metadata.get('display_order', 0))

        if direction == 'down':
            for current_sku in all_skus:
                current_sku_metadata = current_sku.get('metadata', {})
                current_sku_position = current_sku_metadata.get('display_order', None)
                if current_sku_position is None or current_sku['id'] == sku['id'] or int(current_sku_position) <= current_position:
                    continue
                current_sku_position = int(current_sku_position)
                if current_sku_position == current_position + 1:
                    current_sku_metadata['display_order'] = current_sku_position - 1
                else:
                    current_sku_metadata['display_order'] = current_sku_position + 1
                stripe.SKU.modify(
                    current_sku['id'],
                    metadata=current_sku_metadata,
                    api_key=os.environ["STRIPE_SECRET"]
                )

            sku_metadata['display_order'] = current_position + 1
            stripe.SKU.modify(
                sku['id'],
                metadata=sku_metadata,
                api_key=os.environ["STRIPE_SECRET"]
            )
        else:
            for current_sku in all_skus:
                current_sku_metadata = current_sku.get('metadata', {})
                current_sku_position = current_sku_metadata.get('display_order', None)
                if current_sku_position is None or current_sku['id'] == sku['id'] or int(current_sku_position) >= current_position:
                    continue
                current_sku_position = int(current_sku_position)
                if current_sku_position == current_position - 1:
                    current_sku_metadata['display_order'] = current_sku_position + 1
                else:
                    current_sku_metadata['display_order'] = current_sku_position - 1
                stripe.SKU.modify(
                    current_sku['id'],
                    metadata=current_sku_metadata,
                    api_key=os.environ["STRIPE_SECRET"]
                )

            sku_metadata['display_order'] = current_position - 1
            stripe.SKU.modify(
                sku['id'],
                metadata=sku_metadata,
                api_key=os.environ["STRIPE_SECRET"]
            )
        
        cls.list_products(None, response_url, sku['product'])

