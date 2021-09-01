import logging

import azure.functions as func
import azure.durable_functions as df


async def main(mytimer: func.TimerRequest, starter: str) -> None:
    logging.info('BuildSiteFiles Timer Trigger')
    client = df.DurableOrchestrationClient(starter)
    instance_id = await client.start_new("BuildSiteFilesOrchestrator", None, None)
    
    logging.info(f"Started orchestration with ID = '{instance_id}'.")