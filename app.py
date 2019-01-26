import requests
from graphqlclient import GraphQLClient
import json
import csv
from datetime import datetime
import time
from dotenv import DotEnv
from progress.spinner import Spinner
import logging

logging.basicConfig(filename='app.log', filemode="w", format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from utils import (
    get_data_query,
    parse_data,
    get_rate_limit,
    handle_rate_limit,
    write_issues_csv,
    write_repos_csv,
    write_stars_forks,
    clear
)

environment = DotEnv('config/.env')
github_token = environment.get('GITHUB_TOKEN')
client = GraphQLClient('https://api.github.com/graphql')
client.inject_token(f'token {github_token}')

def get_data(query, variables):
    has_next = True
    cursor = None
    entities = []

    spinner = Spinner('Fetching Github Data')
    while has_next:
        spinner.next()
        variables['cursor'] = cursor

        rate_limit = get_rate_limit(client)
        handle_rate_limit(rate_limit)
        results = json.loads(client.execute(query, variables))

        if results['data'] and results['data']['search']['edges']:
            nodes = [ edge['node'] for edge in results['data']['search']['edges']]
            for node in nodes:
                entities.append(parse_data(node))
            has_next = results['data']['search']['pageInfo']['hasNextPage']
            cursor = results['data']['search']['pageInfo']['endCursor']
        else:
            logger.warn(f'No data found: {results}')
            has_next = False


    spinner.finish()
    print('\n')
    return entities

def get_repo_data(org, query_limit):
    variables = {
        "search_query": f"org:{org}",
        "size": query_limit,
    }
    query = get_data_query('graphql/repo_data.gql')

    return get_data(query, variables)

def get_issues_data(org, query_limit):
    """
    Get Github data for the supplied org
    """
    variables = {
        "search_query": f"org:{org}",
        "size": query_limit,
    }
    query = get_data_query('graphql/issues_data.gql')

    return get_data(query, variables)

def get_stars_forks_data(org, repo):
    stars = []
    stars_has_next = True
    forks = []
    forks_has_next = True
    stars_cursor = None
    forks_cursor = None

    spinner = Spinner('Fetching Stars and Forks')
    while stars_has_next or forks_has_next:
        spinner.next()
        variables = {
            "org": org,
            "repoName": repo,
            "size": 100,
            "starsCursor": stars_cursor,
            "forksCursor": forks_cursor,
        }
        query = get_data_query('graphql/stars_forks_data.gql')

        rate_limit = get_rate_limit(client)
        handle_rate_limit(rate_limit)
        results = json.loads(client.execute(query, variables))

        if results['data'] and results['data']['repository']['stargazers']['edges']:
            for edge in results['data']['repository']['stargazers']['edges']:
                stars.append({
                    'owner': org,
                    'repo': repo,
                    'createdAt': edge['starredAt'],
                })

        stars_has_next = results['data']['repository']['stargazers']['pageInfo']['hasNextPage']
        stars_cursor = results['data']['repository']['stargazers']['pageInfo']['endCursor']

        if results['data'] and results['data']['repository']['forks']['edges']:
            nodes = [ edge['node'] for edge in results['data']['repository']['forks']['edges']]

            for node in nodes:
                forks.append({
                    'owner': org,
                    'repo': repo,
                    'createdAt': node['createdAt']
                })

        forks_has_next = results['data']['repository']['forks']['pageInfo']['hasNextPage']
        forks_cursor = results['data']['repository']['forks']['pageInfo']['endCursor']

    spinner.finish()
    return stars, forks

def main():
    processed_orgs = []
    processed_agencies = []
    run_time = datetime.now()

    with open('config/agencies.json', 'r') as agencies_file:
        agencies = json.load(agencies_file)

    for agency, gh_orgs in agencies.items():
        if processed_agencies:
            logger.info(f'Agencies processed: {processed_agencies}')

        logger.info(f'Processing agency: {agency}')
        processed_agencies.append(agency)
        repos = []
        issues = []
        stars = []
        forks = []

        for org in gh_orgs:
            logger.info(f'Processing Github Org: {org}')

            processed_orgs.append(org)

            logger.info('Fetching Repos')
            result_repos = get_repo_data(org, 100)
            repos.extend(result_repos)

            logger.info('Fetching Issues')
            result_issues = get_issues_data(org, 100)
            issues.extend(result_issues)

            for repo in result_repos:
                repo_name = repo['name']
                logger.info(f'Fetching Stars and Forks for repo: {repo_name}')
                result_stars, result_forks = get_stars_forks_data(org, repo_name)
                stars.extend(result_stars)
                forks.extend(result_forks)

        logger.info(f'Processed Orgs: {processed_orgs}')
        logger.info(f'Writing CSV Files for Agency: {agency}')
        write_repos_csv(agency, run_time,repos)
        write_issues_csv(agency, run_time, issues)
        write_stars_forks(agency, run_time, stars, forks,)

        clear()

if if __name__ == "__main__":
    main()
