# This function is not intended to be invoked directly. Instead it will be
# triggered by an HTTP starter function.
# Before running this sample, please:
# - create a Durable activity function (default name is "Hello")
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
import json
from datetime import datetime, timedelta
import azure.functions as func
import azure.durable_functions as df

def orchestrator_function(context: df.DurableOrchestrationContext):
    stages = 8
    on_stage = 1
    outputs = []
    ro = df.RetryOptions(60000, 3)

    while on_stage <= stages:        
        logging.info(f'Calling activity with stage {on_stage}')
        res = yield context.call_activity_with_retry('BuildSiteFiles', ro, f"stage{on_stage}")
        outputs.append(res)
        on_stage = on_stage + 1

    return outputs
    
main = df.Orchestrator.create(orchestrator_function)