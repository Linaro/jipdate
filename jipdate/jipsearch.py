#!/usr/bin/env python3
from argparse import ArgumentParser
import logging as log
import os
import sys
import yaml
from dateutil import parser

# Local files
from jipdate import cfg
from jipdate import jiralogin

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to search tickets in Jira')

    parser.add_argument('-u', '--user', required=False, action="store",
            default=None,
            help='''Query Jira with another Jira username
            (first.last or first.last@linaro.org)''')

    parser.add_argument('-j', '--jql', required=False, action="append",
            default=None,
            help='''JQL string to query Jira. Can be specified several
            times to allow several searches being displayed in the search result.''')

    parser.add_argument('-p', '--project', required=False, action="store",
            default=None,
            help='''Define which project to search in.
            Separate with comma to search in several projects''')

    parser.add_argument('-r', '--reporter', required=False, action="store",
            default=None,
            help='''Search for issues with the specified reporters.
            Use comma to separate multiple reporters.''')

    parser.add_argument('-a', '--assignee', required=False, action="store",
            default=None,
            help='''Search for issues with the specified assignees.
            Use comma to separate multiple reporters.''')

    parser.add_argument('-e', '--epic', required=False, action="store",
            default=None,
            help='''Epic with children, specify epic to view with children.''')

    parser.add_argument('-ca', '--created-after', required=False, action="store",
            default=None,
            help='''Search for issues created after this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".''')

    parser.add_argument('-cb', '--created-before', required=False, action="store",
            default=None,
            help='''Search for issues created before this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".''')

    parser.add_argument('-ua', '--updated-after', required=False, action="store",
            default=None,
            help='''Search for issues updated after this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".''')

    parser.add_argument('-ub', '--updated-before', required=False, action="store",
            default=None,
            help='''Search for issues updated before this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".''')

    parser.add_argument('-c', '--comments', required=False, action="store_true",
            default=False,
            help='''View latest comments.''')

    parser.add_argument('-v', required=False, action="store_true",
            default=False,
            help='''Output some verbose debugging info''')

    parser.add_argument('--dry-run', required=False, action="store_true",
            default=False,
            help='''Do not make any changes to JIRA''')

    return parser


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

def create_jql(jira, initial_jql):
    jql_parts = []
    if initial_jql and initial_jql != "":
        jql_parts.append(initial_jql)

    if cfg.args.project:
        jql_parts.append('project in (%s)' % cfg.args.project)

    if cfg.args.reporter:
        reporter_ids = []
        reporters = cfg.args.reporter.split(',')
        for r in reporters:
            reporter_ids += jira.search_users(query=r)
        if len(reporter_ids) > 0:
            account_ids = []
            for ri in reporter_ids:
                account_ids.append(ri.accountId)
            jql_parts.append('reporter in (%s)' % ','.join(account_ids))

    if cfg.args.assignee:
        assignee_ids = []
        assignees = cfg.args.assignee.split(',')
        for r in assignees:
            assignee_ids += jira.search_users(query=r)
        if len(assignee_ids) > 0:
            account_ids = []
            for ai in assignee_ids:
                account_ids.append(ai.accountId)
            jql_parts.append('assignee in (%s)' % ','.join(account_ids))

    if cfg.args.epic:
        jql_parts.append('(key = %s or parentepic = %s)' % (cfg.args.epic, cfg.args.epic))

    if cfg.args.created_after:
        jql_parts.append('created >= %s' % cfg.args.created_after)

    if cfg.args.created_before:
        jql_parts.append('created <= %s' % cfg.args.created_before)

    if cfg.args.updated_after:
        jql_parts.append('updated >= %s' % cfg.args.updated_after)

    if cfg.args.updated_before:
        jql_parts.append('updated <= %s' % cfg.args.updated_before)

    jql_string = ' AND '.join(jql_parts)

    log.debug(f"{jql_string}")
    return jql_string

def search_issues(jira, jql):
    issues = []
    result = { 'startAt' : 0, 'total' : 1}
    max_results = 50

    while result['startAt'] < result['total']:
        result = jira.search_issues(jql, startAt = result['startAt'], maxResults=max_results, fields=['summary', 'created', 'status', 'issuetype', 'assignee', 'timetracking'], json_result=True)
        issues += result['issues']
        result['startAt'] += max_results

    return issues


def call_jqls(jira, jql):
    issues = []
    for j in jql:
        jql_str = create_jql(jira, j)
        issues += search_issues(jira, jql_str)
    return issues


def print_issues(jira, issues):
    for issue in issues:
        print(f"https://linaro.atlassian.net/browse/{issue['key']} , Type: {issue['fields']['issuetype']['name'].strip()},  Summary: {issue['fields']['summary'].strip()} , Created: {str(parser.parse(issue['fields']['created'])).split(' ')[0]} , Status: {issue['fields']['status']['statusCategory']['name']}")
        if cfg.args.comments:
            c = jira.comments(issue['key'])
            if len(c) > 0:
                try:
                    timespent = issue['fields']['timetracking']['timeSpent']
                except KeyError:
                    timespent = 0
                print(f"# Assignee: {issue['fields']['assignee']['displayName']}, Original Estimate: {issue['fields']['timetracking']['originalEstimate']}, Time Spent: {timespent}")
                print(f"# Last comment, updated: {c[0].updated}, by: {c[0].author}")
                comment = "# ---8<---\n# %s\n# --->8---\n" % \
                          "\n# ".join(c[-1].body.splitlines())
                print(comment)

        #print(f"{issue['key']}, status: {issue['fields']['status']['statusCategory']['name']}, created: {str(parser.parse(issue['fields']['created'])).split(' ')[0]}\n\t   Summary: {issue['fields']['summary']}\n\t   https://linaro.atlassian.net/browse/{issue['key']}")

################################################################################
# Main function
################################################################################
def main():
    argv = sys.argv
    parser = get_parser()
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # The parser arguments (cfg.args) are accessible everywhere after this call.
    cfg.args = parser.parse_args()

    initialize_logger(cfg.args)

    # This initiates the global yml configuration instance so it will be
    # accessible everywhere after this call.
    cfg.initiate_config()

    jira, username = jiralogin.get_jira_instance(False)
    issues = []
    if cfg.args.jql:
        jql = cfg.args.jql
        log.debug(f"JQL: "+jql[0])
        issues = call_jqls(jira, jql)
    else:
        issues = call_jqls(jira, [""])

    print_issues(jira, issues)

if __name__ == "__main__":
    main()
