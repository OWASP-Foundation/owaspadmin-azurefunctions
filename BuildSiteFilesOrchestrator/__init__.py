# This function is not intended to be invoked directly. Instead it will be
# triggered by an HTTP starter function.
# Before running this sample, please:
# - create a Durable activity function (default name is "Hello")
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
import json
from datetime import timedelta
import azure.functions as func
import azure.durable_functions as df


def orchestrator_function(context: df.DurableOrchestrationContext):
    start_two = context.current_utc_datetime + timedelta(minutes=30)
    yield context.call_activity('BuildSiteFiles', "orchestrator")
    yield context.create_timer(start_two)
    yield context.call_activity('BuildSiteFilesTwo', "orchestrator")
  
main = df.Orchestrator.create(orchestrator_function)