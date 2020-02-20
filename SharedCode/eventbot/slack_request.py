import os
import json
import requests
import logging
import azure.functions as func
from .slash_command import SlashCommand
from .view_submission import ViewSubmission
from .block_action import BlockAction

class SlackRequest:
    payload = {}


    def __init__(self, payload={}):
        self.payload = payload


    def get_processor(self):
        if self.__is_command():
            return SlashCommand(self.payload)
        if self.__is_view_submission():
            payload = json.loads(self.payload.get('payload')[0])
            return ViewSubmission(payload)
        if self.__is_block_action():
            payload = json.loads(self.payload.get('payload')[0])
            return BlockAction(payload)


    def __is_command(self):
        if self.payload.get('command', None) is not None:
            return True

        return False


    def __is_block_action(self):
        if self.payload.get('payload', None) is None:
            return False

        payload = json.loads(self.payload.get('payload')[0])

        if payload.get('type', None) == 'block_actions':
            return True

        return False


    def __is_view_submission(self):
        if self.payload.get('payload', None) is None:
            return False

        payload = json.loads(self.payload.get('payload')[0])

        if payload.get('type', None) == 'view_submission':
            return True

        return False

