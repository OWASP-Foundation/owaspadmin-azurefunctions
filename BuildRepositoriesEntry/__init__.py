import datetime
import logging
import os
import json
import time

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
    repos = []
    update = True

    gh = github.OWASPGitHub()
    gh.FindUser('hblankenship') # calling this just to load the libs, etc

    try:
        logging.info('Getting Chapter Repos')
        repos = GetChapterRepos(gh)
    except Exception as err:
        logging.error(f'exception in getting chapter repos: {err}')
        update = False
    
    try:
        logging.info('Getting Project Repos')
        repos.extend(GetProjectRepos(gh))
    except Exception as err:
        logging.error(f'exception in getting project repos: {err}')
        update = False

    try:
        logging.info('Getting Committee Repos')
        repos.extend(GetCommitteeRepos(gh))
    except Exception as err:
        logging.error(f'exception in getting committee repos: {err}')
        update = False

    try:
        logging.info('Getting Event Repos')
        repos.extend(GetEventRepos(gh))
    except Exception as err:
        logging.error(f'exception in getting event repos: {err}')
        update = False
    
    logging.info(f"Got {len(repos)} repositories.")
    if repos and len(repos) > 0 and update:
        table_service = TableService(account_name=os.environ['STORAGE_ACCOUNT'], account_key=os.environ['STORAGE_KEY'])
        table_service.delete_table(table_name=os.environ['REPOSITORY_TABLE']) #delete it to start fresh
        # now wait for actual deletion....
        while(table_service.exists(os.environ['REPOSITORY_TABLE'])):
            time.sleep(5.0)

        table_service.create_table(table_name=os.environ['REPOSITORY_TABLE']) #create if it doesn't exist
    
        while(not table_service.exists(os.environ['REPOSITORY_TABLE'])): # now I have to wait for it here....
            time.sleep(5.0)

        logging.info("Looping through repositories")
        for repo in repos:
            repos_entry = {
                'PartitionKey':'ghrepos',
                'RowKey': repo['name'],
                'Repo': json.dumps(repo)
            }
        
            table_service.insert_or_replace_entity(os.environ['REPOSITORY_TABLE'], entity=repos_entry)
        

    logging.info("function complete")


def GetChapterRepos(gh):
    repos = gh.GetPublicRepositories('www-chapter-')    
    return repos

def GetProjectRepos(gh):
    repos = gh.GetPublicRepositories('www-project')
    return repos

def GetCommitteeRepos(gh):
    repos = gh.GetPublicRepositories('www-committee')
    return repos

def GetEventRepos(gh):
    repos = gh.GetPublicRepositories('www-revent')
    return repos

