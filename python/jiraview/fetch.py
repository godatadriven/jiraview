import requests
import json
import urlparse
import sys
import datetime
import argparse
from iso8601 import parse_date as parse_iso
from pymongo import MongoClient

client = MongoClient()

def log(verbose, s):
    if verbose:
        print s

def fetch_summaries(jql, jira_url, user = None, password = None, verbose = False):
    search_url = urlparse.urljoin(jira_url + '/' if not jira_url.endswith('/') else jira_url, 'rest/api/2/search')

    count = 0
    result = []
    while True:
        search_params = {
            'jql' : jql,
            'fields' : 'updated',
            'expand' : 'schema',
            'maxResults' : 500,
            'startAt' : count
        }

        if (user and password):
            search_request = requests.get(search_url, params = search_params, auth = (user, password))
        else:
            search_request = requests.get(search_url, params = search_params)

        log(verbose, 'Requesting %s.' % search_url)

        search_result = search_request.json()
        result.extend(search_result['issues'])

        count += len(search_result['issues'])
        if count == search_result['total']:
            break

    return result

def fetch_and_save_issues(issues, collection, user = None, password = None, verbose = False):
    count = 0
    for link in issues:
        params = {
            'expand' : 'renderedFields,names,schema,transitions,operations,editmeta,changelog',
            'fields' : '*all'
        }

        if (user and password):
            issue_request = requests.get(link['self'], params = params, auth = (user, password))
        else:
            issue_request = requests.get(link['self'], params = params)

        log(verbose, 'Requesting %s.' % link['self'])

        result = issue_request.json()
        result['_id'] = result['key']
        client.jiraview[collection].save(result)
        count += 1

def most_recent_update(issues):
    return parse_iso(max(i['fields']['updated'] for i in issues))

def parse_args():
    parser = argparse.ArgumentParser(description='Fetch the latest changes for a dataset.')
    parser.add_argument('name', metavar = 'NAME', type = str, help = 'The name of the dataset to fetch.')
    parser.add_argument('-verbose', '-v', dest = 'verbose', action = 'store_true', default = False, help = 'Show some output while work is being done.')
    return parser.parse_args()

def find_dataset(name):
    dataset = client.jiraview.datasets.find_one({ 'name' : name })
    if not dataset:
        print 'Could not find dataset named %s' % args.name
        sys.exit(1)

    return dataset

def main():
    args = parse_args()

    dataset = find_dataset(args.name)

    last_update = dataset.get('last_update') or datetime.datetime(1981, 6, 9)
    # subtract one day to be safe with greater than / equals stuff. Also, I don't know how well JIRA's multi timezone support works (or mine).
    last_update -= datetime.timedelta(days = 1)
    jql = dataset['jql'].format(last_update = last_update.strftime('%Y-%m-%d'))
    log(args.verbose, 'Using JQL query: %s' % jql)

    issues = fetch_summaries(jql, dataset['jira_url'], user = dataset.get('jira_user'), password = dataset.get('jira_password'), verbose = args.verbose)
    log(args.verbose, 'Found %d issues.' % len(issues))

    fetch_and_save_issues(issues, dataset['issue_collection'], user = dataset.get('jira_user'), password = dataset.get('jira_password'), verbose = args.verbose)

    dataset['last_update'] = most_recent_update(issues)
    client.jiraview.datasets.save(dataset)
    log(args.verbose, 'Saving dataset: %s' % str(dataset))

if __name__ == '__main__':
    main()
