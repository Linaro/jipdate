#!/usr/bin/env python3
from argparse import ArgumentParser
from subprocess import call
from time import gmtime, strftime

import json
import os
import re
import sys
import tempfile
import yaml
import datetime

# Local files
import cfg
from helper import vprint, eprint
import jiralogin

import pprint
pprint = pprint.PrettyPrinter().pprint

def add_domain(user):
    """
    Helper function that appends @linaro.org to the username. It does nothing if
    it is already included.
    """
    if '@' not in user:
        user = user + "@linaro.org"
    return user

def enumerate_updates(jira):
    user = cfg.args.user

    since = datetime.datetime.now() - datetime.timedelta(days=7)

    jql = "(project = QLT OR assignee in membersOf('linaro-landing-team-qualcomm')) AND updatedDate > -7d"
    if user:
       jql += ' AND assignee = "%s"' % add_domain(user)
    vprint(jql)

    my_issues = jira.search_issues(jql, expand="changelog", fields="summary,comment,assignee,created")
    if my_issues.total > my_issues.maxResults:
        my_issues = jira.search_issues(jql, expand="changelog", fields="summary,comment,assignee,created",
                                       maxResults=my_issues.total)

    for issue in my_issues:
        changelog = issue.changelog
        comments = issue.fields.comment.comments

        status = {}
        status['issue'] = str(issue)
        if issue.fields.assignee:
            status['assignee'] = issue.fields.assignee.displayName
        else:
            status['assignee'] = 'Unassigned'
        status['summary'] = issue.fields.summary
        status['comments'] = []
        status['resolution'] = None

        created = datetime.datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z')
        if created.replace(tzinfo=None) > since:
            status['resolution'] = 'Created'

        for comment in comments:
            when = datetime.datetime.strptime(comment.created, '%Y-%m-%dT%H:%M:%S.%f%z')
            if when.replace(tzinfo=None) < since:
                continue

            status['comments'].append(comment.body)

        for history in changelog.histories:
            when = datetime.datetime.strptime(history.created, '%Y-%m-%dT%H:%M:%S.%f%z')
            if when.replace(tzinfo=None) < since:
                continue
            for item in history.items:
                if item.field == 'resolution':
                    status['resolution'] = item.toString

        if len(status['comments']) != 0 or status['resolution']:
            yield(status)

def enumerate_pending(jira):
    user = cfg.args.user

    since = datetime.datetime.now() - datetime.timedelta(days=7)

    jql = "(project = QLT OR assignee in membersOf('linaro-landing-team-qualcomm')) AND status = 'In Progress'"
    if user:
       jql += ' AND assignee = "%s"' % add_domain(user)
    vprint(jql)

    my_issues = jira.search_issues(jql, expand="changelog", fields="summary,assignee,created")
    if my_issues.total > my_issues.maxResults:
        my_issues = jira.search_issues(jql, expand="changelog", fields="summary,assignee,created",
                                       maxResults=my_issues.total)

    for issue in my_issues:
        status = {}
        status['issue'] = str(issue)
        if issue.fields.assignee:
            status['assignee'] = issue.fields.assignee.displayName
        else:
            status['assignee'] = 'Unassigned'
        status['summary'] = issue.fields.summary

        created = datetime.datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z')
        status['new'] = created.replace(tzinfo=None) > since

        yield(status)

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to update comments in Jira')

    parser.add_argument('-t', required=False, action="store_true", \
            default=False, \
            help='Use the test server')

    parser.add_argument('-u', '--user', required=False, action="store", \
            default=None, \
            help='Query Jira with another Jira username \
            (first.last or first.last@linaro.org)')

    parser.add_argument('-v', required=False, action="store_true", \
            default=False, \
            help='Output some verbose debugging info')

    return parser

################################################################################
# Main function
################################################################################
def main(argv):
    parser = get_parser()

    # The parser arguments (cfg.args) are accessible everywhere after this call.
    cfg.args = parser.parse_args()

    # This initiates the global yml configuration instance so it will be
    # accessible everywhere after this call.
    cfg.initiate_config()

    jira, username = jiralogin.get_jira_instance(cfg.args.t)

    updates = list(enumerate_updates(jira))
    pendings = list(enumerate_pending(jira))

    assignees = sorted(set([u['assignee'] for u in updates]) | set([p['assignee'] for p in pendings]))
    # Move "Unassigned" issues to the end
    assignees.sort(key='Unassigned'.__eq__)

    for assignee in assignees:
        print("%s:" % assignee)

        issues = [u for u in updates if u['assignee'] == assignee]
        if len(issues) > 0:
            print(' * Past')
            for issue in issues:
                if issue['resolution']:
                    event = 'was %s' % issue['resolution']
                else:
                    event = ''

                print("   * %s (%s) %s" % (issue['summary'], issue['issue'], event))
                for c in issue['comments']:
                    cc = c.splitlines()
                    print("     * " + cc[0])
                    for cc_line in cc[1:]:
                        print("       " + cc_line)

        issues = [p for p in pendings if p['assignee'] == assignee]
        if len(issues) > 0:
            print(' * Ongoing')
            for issue in issues:
                print("   * %s (%s)" % (issue['summary'], issue['issue']))

        print('')

if __name__ == "__main__":
    main(sys.argv)
