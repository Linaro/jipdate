#!/usr/bin/env python3
from argparse import ArgumentParser
from subprocess import call
from time import gmtime, strftime

import json
import logging as log
import os
import re
import sys
import tempfile
import yaml

# Local files
from jipdate import cfg
from jipdate import jiralogin

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to create tickets in Jira')

    parser.add_argument('-f', '--file', required=False, action="store", \
            default=None, \
            help='Create issue from FILE.')

    parser.add_argument('-u', '--user', required=False, action="store", \
            default=None, \
            help='Query Jira with another Jira username \
            (first.last or first.last@linaro.org)')

    parser.add_argument('-v', required=False, action="store_true", \
            default=False, \
            help='Output some verbose debugging info')

    parser.add_argument('--dry-run', required=False, action="store_true", \
            default=False, \
            help='Do not make any changes to JIRA')

    return parser

################################################################################
# Jira functions
################################################################################
def parse_issue_file(new_issue_file):
    """ Reads new issue file and parse it into a python object
    """

    if not os.path.isfile(new_issue_file):
        sys.exit(-1)

    log.debug("Using issue file: %s" % new_issue_file)
    with open(new_issue_file, 'r') as yml:
        yml_issues = yaml.load(yml, Loader=yaml.FullLoader)

    return yml_issues


def initialize_logger(args):
    LOG_FMT = ("[%(levelname)s] %(funcName)s():%(lineno)d   %(message)s")
    lvl = log.ERROR
    if args.v:
        lvl = log.DEBUG

    log.basicConfig(
        # filename="core.log",
        level=lvl,
        format=LOG_FMT,
        filemode='w')


################################################################################
# Main function
################################################################################
def main():
    argv = sys.argv
    parser = get_parser()

    # The parser arguments (cfg.args) are accessible everywhere after this call.
    cfg.args = parser.parse_args()

    initialize_logger(cfg.args)

    # This initiates the global yml configuration instance so it will be
    # accessible everywhere after this call.
    cfg.initiate_config()

    if not cfg.args.file:
        log.error("No file provided\n")
        parser.print_help()
        sys.exit(os.EX_USAGE)

    jira, username = jiralogin.get_jira_instance(False)

    if cfg.args.file is not None:
        filename = cfg.args.file
        issues = parse_issue_file(filename)
        for issue in issues:
            # We should only find one project and one issue type otherwise something is wrong
            issue_meta_data = jira.createmeta(projectKeys=issue['Project'], issuetypeNames=issue['IssueType'], expand='projects.issuetypes.fields')
            issue_fields_dict = {}
            try:
                issue_fields_dict = issue_meta_data['projects'][0]['issuetypes'][0]['fields']
            except IndexError:
                print('Could not get meta data from Jira for project \"' + issue['Project'] + '\" and issue type \"' + issue['IssueType'] + '\"')

            if issue_fields_dict:
                fields = {
                    'project': {'key': issue['Project']},
                    'summary': issue['Summary'],
                    'description': issue['Description'],
                    'issuetype': {'name': issue['IssueType']},
                    'timetracking': {'originalEstimate': issue['OriginalEstimate']}
                }

                if 'AssigneeEmail' in issue.keys():
                    assignee = jira.search_assignable_users_for_issues(query=issue['AssigneeEmail'], project=issue['Project'])
                    # We assume that the first entry in the returned user array is the one we want
                    if len(assignee) > 0:
                        fields['assignee'] = {'id': assignee[0].accountId}

                if 'EpicLink' in issue.keys():
                    fields['customfield_10014'] = issue['EpicLink']

                if 'Component' in issue.keys():
                    components = jira.project_components(issue['Project'])
                    for c in components:
                        if c.name == issue['Component']:
                            fields['components'] = [{'id': str(c.id)}]

                sprint_found = True  # Only indicate sprint not found in case a sprint has been specified.
                if 'Sprint' in issue.keys():
                    sprint_found = False
                    boards_in_project = jira.boards(projectKeyOrID=issue['Project'])
                    for board in boards_in_project:
                        sprints_in_board = jira.sprints(board_id=board.id)
                        for sprint in sprints_in_board:
                            if sprint.name == issue['Sprint']:
                                fields['customfield_10020'] = sprint.id
                                print('Found '+ sprint.name + ' ' + str(sprint.id))
                                sprint_found = True

                if sprint_found:
                    print(fields)
                    new_issue = jira.create_issue(fields=fields)
                    server = cfg.get_server()
                    print(f"New issue created: {server.get('url')}/browse/{new_issue}")
                else:
                    print('Sprint \"' + issue['Sprint'] + '\" not found in project ' + issue['Project'])
    else:
        log.error("Trying to run script with unsupported configuration. Try using --help.")
        sys.exit(os.EX_USAGE)

if __name__ == "__main__":
    main()
