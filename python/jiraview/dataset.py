from pymongo import MongoClient
import argparse

client = MongoClient()

def save_dataset(name, jql = None, issue_collection = None, jira_url = None, jira_user = None, jira_password = None, reset = False):
    dataset = client.jiraview.datasets.find_one({ 'name' : name} ) or {}
    dataset['name'] = name

    if jql: dataset['jql'] = jql
    if issue_collection: dataset['issue_collection'] = issue_collection
    if jira_url: dataset['jira_url'] = jira_url
    if jira_user: dataset['jira_user'] = jira_user
    if jira_password: dataset['jira_password'] = jira_password
    if reset:
        dataset['last_update'] = None

    client.jiraview.datasets.save(dataset)
    print 'Saved: %s' % str(dataset)

def delete_dataset(name):
    pass

def parse_args():
    parser = argparse.ArgumentParser(description='Create, modify or delete datasets.')
    parser.add_argument('name', metavar = 'NAME', type = str, help = 'The name of the dataset to modify.')
    parser.add_argument('-jql', metavar = 'QUERY', type = str, help = 'The JQL query to fire against JIRA to populate this dataset. In the query, use {last_update} to substitute the date that the dataset was last updated in a JIRA friendly format. This enables incremental fetching.')
    parser.add_argument('-collection', metavar = 'ISSUE_COLLECTION', type = str, dest = 'issue_collection', help = 'The MongoDB collection to use for storing issues in this dataset.')
    parser.add_argument('-url', metavar = 'JIRA_URL', type = str, dest = 'jira_url', help = 'The JIRA base URL.')
    parser.add_argument('-user', metavar = 'JIRA_USER', type = str, dest = 'jira_user', help = 'The JIRA username to authenticate with.')
    parser.add_argument('-password', metavar = 'JIRA_PASSWORD', type = str, dest = 'jira_password', help = 'This JIRA password to authenticate with.')
    parser.add_argument('-reset', dest = 'reset', action = 'store_true', default = False, help = 'Reset the last_update date for this dataset. Next fetch will fetch the entire set instead of incremental.')

    return parser.parse_args()

def main():
    save_dataset(**vars(parse_args()))

if __name__ == '__main__':
    main()
