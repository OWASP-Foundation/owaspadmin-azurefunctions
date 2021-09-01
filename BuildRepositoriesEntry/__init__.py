import datetime
import logging
import os
import json

import azure.functions as func
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity

from ..SharedCode.github import OWASPGitHub

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')
    logging.info('BuildRespositoriesEntry function ran at %s', utc_timestamp)

    gh = OWASPGitHub()
    repos = gh.GetPublicRepositories('www-')

    repos_entry = {
        'PartitionKey':'ghrepos',
        'RowKey': 'current',
        'Repos': json.dumps(repos)
    }

    table_service = TableService(account_name=os.environ['STORAGE_ACCOUNT'], account_key=os.environ['STORAGE_KEY'])
    table_service.create_table(table_name=os.environ['REPOSITORY_TABLE']) #create if it doesn't exist
    ip_row = None
    try:
        ip_row = table_service.get_entity(os.environ['REPOSITORY_TABLE'], repos_entry['PartitionKey'], repos_entry['RowKey'])
    except:
        pass
    if not ip_row:
        table_service.insert_entity(table_name=os.environ['REPOSITORY_TABLE'], entity=repos_entry)
        ip_row = repos_entry
    else:
        table_service.update_entity(os.environ['REPOSITORY_TABLE'], ip_row)
