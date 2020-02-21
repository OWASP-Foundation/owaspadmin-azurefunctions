import os
import json
import requests
import logging
import azure.functions as func

class SlackResponse:
    content = {}
    response_type = 'acknowledgement'
    trigger_id = None
    response_url = None


    def __init__(
            self,
            response_type='acknowledgement',
            trigger_id=None,
            response_url=None,
            content={}
    ):
        self.response_type = response_type
        self.trigger_id = trigger_id
        self.response_url = response_url
        self.content = content


    @classmethod
    def modal(
            cls,
            title,
            callback_id=None,
            trigger_id=None,
            response_url=None,
            submit_label='Create',
            close_label='Cancel'
    ):
        modal_content = {
            'type': 'modal',
            'title': {
                'type': 'plain_text',
                'text': title,
                'emoji': True
            },
            'submit': {
                'type': 'plain_text',
                'text': submit_label,
                'emoji': True
            },
            'close': {
                'type': 'plain_text',
                'text': close_label,
                'emoji': True
            },
            'blocks': []
        }

        if response_url is not None:
            modal_content['private_metadata'] = response_url

        if callback_id is not None:
            modal_content['callback_id'] = callback_id

        return cls(
            response_type='modal',
            content=modal_content,
            trigger_id=trigger_id,
            response_url=response_url
        )


    @classmethod
    def acknowledgement(cls):
        return cls(response_type='acknowledgement')


    @classmethod
    def message(cls, response_url=None, text=None, trigger_id=None):
        return cls(
            response_type='message',
            response_url=response_url,
            trigger_id=trigger_id,
            content={
                'text': text,
                'blocks': []
            }
        )


    def add_block(self, block_content):
        self.content['blocks'].append(block_content)


    def add_error_response_blocks(self, error_message):
        self.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":exclamation: *Error*"
            }
        })
        self.add_block({
            "type": "divider"
        })
        self.add_block({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": error_message
            }
        })
        self.add_block({
            "type": "divider"
        })


    def send(self):
        if self.response_type == 'modal':
            return self.__send_modal_response()
        if self.response_type == 'message':
            return self.__send_message_response()

        return self.__send_acknowledgement_response()


    def __send_modal_response(self):
        response_json = {
            'view': self.content
        }

        if self.trigger_id is not None:
            response_json['trigger_id'] = self.trigger_id

        requests.post(
            'https://slack.com/api/views.open',
            json=response_json,
            headers={
                "Content-type": "application/json",
                "Authorization": "Bearer " + os.environ["SL_ACCESS_TOKEN"]
            }
        )

    def __send_message_response(self):
        response_json = self.content

        if self.response_url is not None:
            requests.post(
                self.response_url,
                json=response_json,
                headers={
                    "Content-type": "application/json"
                }
            )
        else:
            logging.info('sending message #######')
        

    def __send_acknowledgement_response(self):
        return func.HttpResponse(
            body='',
            status_code=200
        )
