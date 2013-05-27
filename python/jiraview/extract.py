import argparse
from iso8601 import parse_date as parse_iso
from iso8601 import iso8601
import datetime
import os
import codecs
import csv
from pymongo import MongoClient

client = None

def create_client():
    global client
    if not client:
        client = MongoClient()

as_is_fields = {
    'key': 'key',
    # 'summary' : 'fields.summary', # PROBLEMATIC IN CSV! Will contain new lines and such.
    'issue_type' : 'fields.issuetype.name',
    'vote_count' : 'fields.votes.votes',
    'resolution' : 'fields.resolution.name',
    'resolutiondate' : 'fields.resolutiondate',
    'reporter' : 'fields.reporter.name',
    'updated' : 'fields.updated',
    'created' : 'fields.created',
    # 'description' : 'fields.description', # PROBLEMATIC IN CSV! Will contain new lines and such.
    'priority' : 'fields.priority.name',
    'watch_count' : 'fields.watches.watchCount',
    'status' : 'fields.status.name',
    'assignee' : 'fields.assignee.name',
    'project' : 'fields.project.key',
    'comment_count' : 'fields.comment.total'
}

def retrieve_dotnotation_field(input_dict, input_key):
    return reduce(lambda d, k: d.get(k) if d else None, input_key.split("."), input_dict)

def find_dataset(name):
    dataset = client.jiraview.datasets.find_one({ 'name' : name })
    if not dataset:
        print 'Could not find dataset named %s' % args.name
        sys.exit(1)

    return dataset

def get_issues(collection):
    return [issue for issue in client.jiraview[collection].find()]

def add_transitions_to_issues(issues):
    for issue in issues:
        # filter histories for changes that involve the status field
        log = issue['changelog']['histories']
        workflow_log = [ line for line in log if 'status' in [i['field'] for i in line['items']] ]

        #remove non status related items from log
        for line in workflow_log:
            line['status_item'], = filter(lambda i: i['field'] == 'status', line['items'])

        # Not sure if they come in sorted order
        workflow_log.sort(key = lambda x: x['created'])

        # Create a list from the from 'nothing' to Open transition and the rest of the transitions
        transitions = [{
            'transition' : 'Non-existent to Open',
            'when' : retrieve_dotnotation_field(issue, 'fields.created'),
            'who' : retrieve_dotnotation_field(issue, 'fields.reporter.name'),
            'from_status' : None,
            'to_status' : 'Open',
            'days_in_from_status' : None,
            'days_since_open' : None
        }] + [{
            'transition' : '%s to %s' % (retrieve_dotnotation_field(line, 'status_item.fromString'), retrieve_dotnotation_field(line, 'status_item.toString')),
            'when' : retrieve_dotnotation_field(line, 'created'),
            'who' : retrieve_dotnotation_field(line, 'author.name'),
            'from_status' : retrieve_dotnotation_field(line, 'status_item.fromString'),
            'to_status' : retrieve_dotnotation_field(line, 'status_item.toString'),
            'days_since_open' : (parse_iso(retrieve_dotnotation_field(line, 'created')) - parse_iso(retrieve_dotnotation_field(issue, 'fields.created'))).total_seconds() / (24 * 3600)
        } for line in workflow_log]

        # Calculate days between transitions
        for idx in xrange(1, len(transitions)):
            transitions[idx]['days_in_from_status'] = (parse_iso(transitions[idx]['when']) - parse_iso(transitions[idx - 1]['when'])).total_seconds() / (24 * 3600)

        issue['__transitions'] = transitions

def issue_fields(issue):
    result = {}

    # Add basic fields
    for field_name, dotted_field in as_is_fields.items():
        result[field_name] = retrieve_dotnotation_field(issue, dotted_field)

    # Calculate # of days in current status
    result['days_in_current_status'] = (datetime.datetime.now(iso8601.Utc()) - parse_iso(issue['__transitions'][-1]['when'])).total_seconds() / (24 * 3600)

    return result

def write_issues(basename, dir, issues):
    if len(issues) == 0:
        return

    with codecs.open(os.path.join(dir, basename + '-issues.csv'), 'w', 'utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, issue_fields(issues[0]).keys(), restval = 'NA', dialect = 'excel')
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue_fields(issue))


def write_transitions(basename, dir, issues):
    if len(issues) == 0:
        return

    with codecs.open(os.path.join(dir, basename + '-transitions.csv'), 'w', 'utf-8') as csv_file:
        row = issue_fields(issues[0])
        row.update(issues[0]['__transitions'][0])

        writer = csv.DictWriter(csv_file, row.keys(), restval = 'NA', dialect = 'excel')
        writer.writeheader()
        for issue in issues:
            row = issue_fields(issue)
            for transition in issue['__transitions']:
                row.update(transition)
                writer.writerow(row)

def all_transitions_and_known_statuses(issues):
    known_statuses = set()
    transitions = []
    for issue in issues:
        transitions.extend(issue['__transitions'])

    for transition in transitions:
        known_statuses.add(transition['from_status'])
        known_statuses.add(transition['to_status'])

    transitions.sort(key = lambda x: x['when'])

    return (transitions, known_statuses)

def write_issue_counts(basename, dir, issues):
    if len(issues) == 0:
        return

    with codecs.open(os.path.join(dir, basename + '-daycounts.csv'), 'w', 'utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, ['day', 'status', 'count'], restval = 'NA', dialect = 'excel')
        writer.writeheader()

        #TODO: prettify garble, probably want to create a generator for the days
        transitions, known_statuses = all_transitions_and_known_statuses(issues)

        issue_counts = { s : 0 for s in known_statuses }

        one_day = datetime.timedelta(days = 1)
        day = parse_iso(transitions[0]['when'])
        itr = iter(transitions)
        line = itr.next()
        while day <= parse_iso(transitions[-1]['when']):
            while parse_iso(line['when']) < day:
                issue_counts[line['from_status']] -= 1
                issue_counts[line['to_status']] += 1
                line = itr.next()

            rows = [
                {
                    'day' : day.isoformat(),
                    'status' : k,
                    'count' : v
                } for k,v in issue_counts.items() if k != None ]
            for row in rows:
                writer.writerow(row)

            day += one_day

def parse_args():
    parser = argparse.ArgumentParser(description = 'Create CSV files for issues from a dataset.')
    parser.add_argument('name', metavar = 'NAME', type = str, help = 'The name of the dataset to extract.')
    parser.add_argument('-basename', metavar = 'BASE_FILENAME', type = str, help = 'Base filename for the CSV files. The program will create three files: [basename]-issues.csv, [basename]-transitions.csv and [basename]-daycounts.csv.')
    parser.add_argument('-dir', metavar = 'OUTPUT_DIRECTORY', type = str, default = '.', help = 'Output directory.')

    return parser.parse_args()

def main():
    args = parse_args()

    create_client()

    dataset = find_dataset(args.name)
    issues = get_issues(dataset['issue_collection'])

    add_transitions_to_issues(issues)

    write_issue_counts(args.basename or args.name, args.dir, issues)
    write_issues(args.basename or args.name, args.dir, issues)
    write_transitions(args.basename or args.name, args.dir, issues)

if __name__ == '__main__':
    main()
