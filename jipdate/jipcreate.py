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


jira_field_to_yaml = {
        'issuetype' : 'IssueType',
        'project' : 'Project',
        'summary' : 'Summary',
        'description' : 'Description',
        'assignee' : 'AssigneeEmail',
        'customfield_10014' : 'EpicLink',
        'customfield_10104' : 'ClientStakeholder',
        'timetracking' : 'OriginalEstimate',
        'components' : 'Components',
        'customfield_10020' : 'Sprint',
        'duedate' : 'Due date',
        'customfield_10011' : 'Epic Name',
        'customfield_10034' : 'Share Visibility',
        }

################################################################################
# Main function
################################################################################
def main():
    argv = sys.argv
    parser = get_parser()
    created_cards = {}

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
            issue_fields_dict = {}
            try:
                issue_meta_data = jira.createmeta(projectKeys=issue['Project'], issuetypeNames=issue['IssueType'], expand='projects.issuetypes.fields')
                issue_fields_dict = issue_meta_data['projects'][0]['issuetypes'][0]['fields']
                log.debug(f"Project: {issue['Project']}")
                log.debug(f"IssueType: {issue['IssueType']}")
                log.debug(f"issue fields dict: {issue_fields_dict}")
            except (IndexError, KeyError):
                print(f"Please specify 'Project' and 'IssueType'.")

            if issue_fields_dict:
                fields = {
                    'project': {'key': issue['Project']},
                    'issuetype': {'name': issue['IssueType']},
                }

                if 'Summary' in issue.keys():
                    fields['summary'] = issue['Summary']

                if 'Description' in issue.keys():
                    fields['description'] = issue['Description']

                if 'OriginalEstimate' in issue.keys():
                    fields['timetracking'] = {'originalEstimate': issue['OriginalEstimate']}

                if 'AssigneeEmail' in issue.keys():
                    assignee = jira.search_assignable_users_for_issues(query=issue['AssigneeEmail'], project=issue['Project'])
                    log.debug(f"Assignee email: {issue['AssigneeEmail']}")
                    log.debug(f"Assignee: {assignee}")
                    # We assume that the first entry in the returned user array is the one we want
                    if len(assignee) > 0:
                        fields['assignee'] = {'id': assignee[0].accountId}

                if 'EpicLink' in issue.keys():
                    if issue['EpicLink'] in created_cards.keys():
                        fields['customfield_10014'] = created_cards[issue['EpicLink']]
                    else:
                        fields['customfield_10014'] = issue['EpicLink']

                if 'ClientStakeholder' in issue.keys():
                    csh_fields_dict = issue_meta_data['projects'][0]['issuetypes'][0]['fields']['customfield_10104']['allowedValues']
                    for s in csh_fields_dict:
                        if s['value'] == issue['ClientStakeholder']:
                            fields['customfield_10104'] = [{'self':s['self'], 'value': s['value'], 'id': str(s['id'])}]

                if 'Components' in issue.keys():
                    components = jira.project_components(issue['Project'])
                    comparr = []
                    for c in components:
                        for comp in issue['Components'].split(','):
                            if c.name == comp.strip():
                                comparr.append({'id': str(c.id)})
                    if len(comparr) > 0:
                        fields['components'] = comparr

                sprint_found = True  # Only indicate sprint not found in case a sprint has been specified.
                if 'Sprint' in issue.keys():
                    sprint_found = False
                    boards_in_project = jira.boards(projectKeyOrID=issue['Project'])
                    log.debug(f"Boards:")
                    for board in boards_in_project:
                        log.debug(f"* {board}")
                        sprints_in_board = jira.sprints(board_id=board.id)
                        log.debug(f" + Sprints:")
                        for sprint in sprints_in_board:
                            log.debug(f"  - {sprint}")
                            if sprint.name == issue['Sprint']:
                                fields['customfield_10020'] = sprint.id
                                sprint_found = True

                if 'Due date' in issue.keys():
                    fields['duedate'] = str(issue['Due date'])

                if 'IssueType' in issue.keys() and issue['IssueType'] == 'Epic':
                    if 'Epic Name' in issue.keys():
                        fields['customfield_10011'] = issue['Epic Name']
                    else:
                        fields['customfield_10011'] = issue['Summary']

                if 'Share Visibility' in issue.keys():
                    share_visibility = []
                    for shared_with in issue['Share Visibility']:
                        tmp_share = jira.search_assignable_users_for_issues(query=shared_with, project=issue['Project'])[0]
                        share_visibility.append({'id': tmp_share.accountId})
                    log.debug(f"shared with: {issue['Share Visibility']}")
                    log.debug(f"share_visibility: {share_visibility}")
                    # We assume that the first entry in the returned user array is the one we want
                    if len(share_visibility) > 0:
                        fields['customfield_10034'] = share_visibility

                if sprint_found:
                    # Check if all feilds are possible to set in this issuetype and project.
                    for field in fields.keys():
                        if field not in issue_fields_dict.keys():
                            print(f"Field {field} set by script but not possible for issuetype and project in Jira.")
                            sys.exit(os.EX_USAGE)

                    # Check fields required by Jira.
                    for field in issue_fields_dict.keys():
                        if issue_fields_dict[field]['required'] and not issue_fields_dict[field]['hasDefaultValue']:
                            if field not in fields.keys():
                                print(f"Field {jira_field_to_yaml[field]} required but not set.")
                                sys.exit(os.EX_USAGE)

                    if cfg.args.dry_run:
                        print(f"This issue would have been created when running without '--dry-run':")
                        created_cards [ issue['Summary'] ] = f"new_issue, {issue['Summary']}"
                        for field in fields.keys():
                            print(f"{field}: {fields[field]}")
                    else:
                        server = cfg.get_server()
                        new_issue = jira.create_issue(fields=fields)
                        created_cards [ issue['Summary'] ] = str(new_issue)
                        print(f"New issue created: {server.get('url')}/browse/{new_issue}")
                else:
                    print('Sprint \"' + issue['Sprint'] + '\" not found in project ' + issue['Project'])
    else:
        log.error("Trying to run script with unsupported configuration. Try using --help.")
        sys.exit(os.EX_USAGE)

if __name__ == "__main__":
    main()
