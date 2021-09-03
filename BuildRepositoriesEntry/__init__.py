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

    gh = github.OWASPGitHub()
    ch_repos = gh.GetPublicRepositories('www-chapter-')
    pr_repos = gh.GetPublicRepositories('www-project-')
    cm_repos = gh.GetPublicRepositories('www-committee-')
    ev_repos = gh.GetPublicRepositories('www-revent-')
    repos = []
    repos.append(ch_repos)
    repos.append(pr_repos)
    repos.append(cm_repos)
    repos.append(ev_repos)
    
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

    logging.info("function complete")