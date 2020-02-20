import os
import json
import requests
import logging
import azure.functions as func
from .slack_response import SlackResponse
from .event import Event

class SlashCommand:
    command = None
    text = None
    response_url = None
    trigger_id = None


    def __init__(self, payload={}):
        self.command = payload.get('command', None)[0]
        text = payload.get('text', None)
        if text is not None:
            self.text = payload.get('text')[0]

        response_url = payload.get('response_url', None)
        if response_url is not None:
            self.response_url = response_url[0]

        trigger_id = payload.get('trigger_id', None)
        if trigger_id is not None:
            self.trigger_id = trigger_id[0]


    def process(self, queue):
        if self.text == 'create':
            self.__handle_create_event()
        elif self.text == 'list':
            self.__handle_list_event(queue)
        else:
            self.__handle_all_event(queue)

        acknowledgement = SlackResponse.acknowledgement()
        return acknowledgement.send()


    def __handle_create_event(self, queue):
        Event.show_create_form(
            trigger_id=self.trigger_id,
            response_url=self.response_url
        )


    def __handle_list_event(self, queue):
        Event.queue_list_events(
            response_url=self.response_url,
            queue=queue
        )

    def __handle_all_event(self, queue):
        Event.all_options(
            response_url=self.response_url
        )
