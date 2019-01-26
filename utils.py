import csv
import json
from datetime import datetime
import time
from os import system, name

def clear():
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')

def get_data_query(file_name):
    """
    Get GH query for supplied GH organization
    """
    with open(file_name, 'r') as graphql_query:
        return graphql_query.read()

def parse_repo_data(node):

    return {
        'name': node['name'],
        'owner': node['owner']['login'],
        'issues': node['issues']['totalCount'],
        'forks': node['forks']['totalCount'],
        'stargazers': node['stargazers']['totalCount'],
        'watchers': node['watchers']['totalCount'],
        'forkCount': node['forkCount'],
        'full_name': node['nameWithOwner'],
        'created_at': node['createdAt'],
        'isPrivate': node['isPrivate'],
    }

def parse_issue_data(node):
    return {
        'type': node['__typename'],
        'owner': node['repository']['owner']['login'],
        'repo_name': node['repository']['name'],
        'title': node['title'],
        'created_at': node['createdAt'],
        'last_edit_date': node['lastEditedAt'],
        'state': node['state'],
        'updated_at': node['updatedAt'],
    }

def parse_data(node):
    """
    Parse Github node data.
    """
    if node['__typename'] == 'Repository':
        return parse_repo_data(node)
    if node['__typename'] == 'Issue' or node['__typename'] == 'PullRequest':
        return parse_issue_data(node)

def create_csv(file_name, data, fields):
    """
    Create a CSV file from the supplied data and fields
    """
    with open(f'data/{file_name}', 'w') as csv_file:

        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)

def write_issues_csv(owner, run_time, data):
    """
    Write issues to a CSV file
    """
    fields = [
        'type',
        'owner',
        'repo_name',
        'title',
        'created_at',
        'last_edit_date',
        'state',
        'updated_at',
    ]
    create_csv(f'github-{owner}-issues-data-{run_time}.csv', data, fields)

def write_repos_csv(owner, run_time, data):
    """
    Write repos to a CSV file
    """
    fields = [
        'name',
        'owner',
        'issues',
        'forks',
        'stargazers',
        'watchers',
        'forkCount',
        'full_name',
        'created_at',
        'isPrivate',
    ]
    create_csv(f'github-{owner}-repos-data-{run_time}.csv', data, fields)

def write_stars_forks(owner, run_time, stars, forks):
    fields = ['owner', 'repo', 'createdAt']

    create_csv(f'github-{owner}-stars-data-{run_time}.csv', stars, fields)
    create_csv(f'github-{owner}-forks-data-{run_time}.csv', forks, fields)

def get_rate_limit(client):
    """
    Get the Github API rate limit current state for the used token
    """
    query = '''query {
        rateLimit {
            limit
            remaining
            resetAt
        }
    }'''
    response = client.execute(query)
    json_response = json.loads(response)
    return json_response['data']['rateLimit']

def handle_rate_limit(rate_limit):
    """
    Handle Github API rate limit and wait times
    """
    remaining = rate_limit['remaining']
    limit = rate_limit['limit']
    percent_remaining = remaining / limit
    reset_at = rate_limit['resetAt']
    if percent_remaining < 0.15:
        reset_at = datetime.strptime(reset_at, '%Y-%m-%dT%H:%M:%SZ')
        current_time = datetime.now()
        time_diff = reset_at - current_time
        seconds = time_diff.total_seconds()

        print(f'Rate Limit hit. Waiting for reset.\nProcess will continue at: {reset_at}')

        time.sleep(seconds)
