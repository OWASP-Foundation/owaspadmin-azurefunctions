import datetime
import logging
import os
import json

import azure.functions as func
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity

from ..SharedCode import github

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')
    logging.info('BuildRespositoriesEntry function ran at %s', utc_timestamp)

    try:
        gh = github.OWASPGitHub()
        ch_repos = gh.GetPublicRepositories('www-chapter-')
        pr_repos = gh.GetPublicRepositories('www-project-')
        cm_repos = gh.GetPublicRepositories('www-committee-')
        ev_repos = gh.GetPublicRepositories('www-revent-')
        repos = []
        repos.extend(ch_repos)
        repos.extend(pr_repos)
        repos.extend(cm_repos)
        repos.extend(ev_repos)
    except Exception as err: 
        logging.warn(f'exception in getting repos: {err}')

    logging.info(f"Got {len(repos)} repositories.")
    
    table_service = TableService(account_name=os.environ['STORAGE_ACCOUNT'], account_key=os.environ['STORAGE_KEY'])
    table_service.create_table(table_name=os.environ['REPOSITORY_TABLE']) #create if it doesn't exist
    
    logging.info("Looping through repositories")
    for repo in repos:
        repos_entry = {
            'PartitionKey':'ghrepos',
            'RowKey': repo['name'],
            'Repo': json.dumps(repo)
        }
        
        table_service.insert_or_replace_entity(os.environ['REPOSITORY_TABLE'], entity=repos_entry)
        

    logging.info("function complete")