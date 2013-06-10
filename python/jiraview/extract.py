# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

import argparse
from iso8601 import parse_date as parse_iso
from iso8601 import iso8601
import datetime
import os
import csv
from pymongo import MongoClient

import jvutil as util

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

def add_user_transitions_to_issues(issues, user_transitions):
    all_from_statuses = [ user_transition.split('-')[0].lower() for user_transition in user_transitions.values() ]
    all_to_statuses = [ user_transition.split('-')[1].lower() for user_transition in user_transitions.values() ]

    for issue in issues:
        from_status_times = {}
        to_status_times = {}
        # Register only the first change to from status and always the last change to to status
        for transition in issue['__transitions']:
            status = transition['to_status'].lower().replace(' ', '')
            if not status in from_status_times and status in all_from_statuses:
                from_status_times[status] = transition['when']
            if status in all_to_statuses:
                to_status_times[status] = transition['when']

        result = {}
        for user_transition_key, user_transition_value in user_transitions.items():
            from_status = user_transition_value.split('-')[0].lower()
            to_status = user_transition_value.split('-')[1].lower()
            result[user_transition_key] = (parse_iso(to_status_times[to_status]) - parse_iso(from_status_times[from_status])).total_seconds() / (24 * 3600) if (from_status in from_status_times) and (to_status in to_status_times) else 'NA'
            result['first_time_in_' + from_status] = from_status_times[from_status] if from_status in from_status_times else 'NA'
            result['last_time_in_' + to_status] = to_status_times[to_status] if to_status in to_status_times else 'NA'

        issue['__user_transitions'] = result

def issue_fields(issue):
    result = {}

    # Add basic fields
    for field_name, dotted_field in as_is_fields.items():
        result[field_name] = retrieve_dotnotation_field(issue, dotted_field)

    # Add user transitions
    for field_name, field_value in issue['__user_transitions'].items():
        result[field_name] = field_value

    # Calculate # of days in current status
    result['days_in_current_status'] = (datetime.datetime.now(iso8601.Utc()) - parse_iso(issue['__transitions'][-1]['when'])).total_seconds() / (24 * 3600)

    # Add character lenghts for some fields
    description_field = retrieve_dotnotation_field(issue, 'fields.description')
    summary_field = retrieve_dotnotation_field(issue, 'fields.summary')
    result['description_length'] = len(description_field) if description_field else None
    result['summary_length'] = len(summary_field) if summary_field else None

    return result

def write_issues(basename, dir, issues):
    if len(issues) == 0:
        return

    with open(os.path.join(dir, basename + '-issues.csv'), 'w') as csv_file:
        writer = util.Utf8CsvDictWriter(csv_file, issue_fields(issues[0]).keys())
        for issue in issues:
            writer.writerow(issue_fields(issue))


def write_transitions(basename, dir, issues):
    if len(issues) == 0:
        return

    with open(os.path.join(dir, basename + '-transitions.csv'), 'w') as csv_file:
        row = issue_fields(issues[0])
        row.update(issues[0]['__transitions'][0])

        writer = util.Utf8CsvDictWriter(csv_file, row.keys())
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

    with open(os.path.join(dir, basename + '-daycounts.csv'), 'w') as csv_file:
        writer = util.Utf8CsvDictWriter(csv_file, ['day', 'status', 'count'])

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

def add_user_defined_fields(fields):
    as_is_fields.update(fields)


def parse_args():
    class DictAction(argparse.Action):
        def __call__(self, parser, namespace, option_values, option_string):
            d = getattr(namespace, self.dest, {})
            d.update( { k : v for k,v in [option_value.split('=') for option_value in option_values] })
            setattr(namespace, self.dest, d)

    parser = argparse.ArgumentParser(description = 'Create CSV files for issues from a dataset.')
    parser.add_argument('name', metavar = 'NAME', type = str, help = 'The name of the dataset to extract.')
    parser.add_argument('-basename', metavar = 'BASE_FILENAME', type = str, help = 'Base filename for the CSV files. The program will create three files: [basename]-issues.csv, [basename]-transitions.csv and [basename]-daycounts.csv.')
    parser.add_argument('-dir', metavar = 'OUTPUT_DIRECTORY', type = str, default = '.', help = 'Output directory.')
    parser.add_argument('-fields', metavar = 'ADDITIONAL_FIELD', type = str, nargs = '*', default = {}, action = DictAction, help = 'List of additional fields to be added to each issue. E.g. "-fields team=fields.custom3368.value magic=fields.customfield2091.value"')
    parser.add_argument('-transitions', metavar = 'ADDITIONAL_LONG_TRANSITIONS', type = str, nargs = '*', default = {}, action = DictAction, help = 'List of end-to-end transition information to add to the output CSV. E.g. "-transitions resolution_time=open-resolved progress_time=inprogress-closed" will add the number of days between statuses as field to the CSV. Status names are case-insensitive but with spaces removed.')

    return parser.parse_args()

def main():
    args = parse_args()
    add_user_defined_fields(args.fields)

    create_client()

    dataset = find_dataset(args.name)
    issues = get_issues(dataset['issue_collection'])

    add_transitions_to_issues(issues)
    add_user_transitions_to_issues(issues, args.transitions)

    write_issues(args.basename or args.name, args.dir, issues)
    write_issue_counts(args.basename or args.name, args.dir, issues)
    write_transitions(args.basename or args.name, args.dir, issues)

if __name__ == '__main__':
    main()
