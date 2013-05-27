from pymongo import MongoClient
import codecs
import sys
import argparse
import os
import json

client = None

def create_client():
    global client
    if not client:
        client = MongoClient()

def find_dataset(name):
    dataset = client.jiraview.datasets.find_one({ 'name' : name })
    if not dataset:
        print 'Could not find dataset named %s' % args.name
        sys.exit(1)

    return dataset

def get_issues(collection):
    return [issue for issue in client.jiraview[collection].find()]


def write_issues_json(basename, dir, issues):
    if len(issues) == 0:
        return

    with codecs.open(os.path.join(dir, basename + '-issues.json'), 'w', 'utf-8') as json_file:
        for issue in issues:
            json_file.write(json.dumps(issue))
            json_file.write('\n')

def parse_args():
    parser = argparse.ArgumentParser(description = 'Export a JSON file of all issues, one issue per line (and one line per issue).')
    parser.add_argument('name', metavar = 'NAME', type = str, help = 'The name of the dataset to extract.')
    parser.add_argument('-basename', metavar = 'BASE_FILENAME', type = str, help = 'Base filename for the XES file. The program will create [basename]-process.xes.')
    parser.add_argument('-dir', metavar = 'OUTPUT_DIRECTORY', type = str, default = '.', help = 'Output directory')

    return parser.parse_args()

def main():
    args = parse_args()


if __name__ == '__main__':
    args = parse_args()

    create_client()

    dataset = find_dataset(args.name)
    issues = get_issues(dataset['issue_collection'])

    write_issues_json(args.basename or args.name, args.dir, issues)
