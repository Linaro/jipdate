#!/usr/bin/env python3
from argparse import ArgumentParser
from subprocess import call
from time import gmtime, strftime
from jinja2 import Template

import datetime
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

def default_jql():
    user = cfg.args.user
    project = cfg.args.project
    team = cfg.args.team

    if team and project:
        jql = "(project = %s or assignee in membersOf('%s')) " % (project, team)
    elif team:
        jql = "assignee in membersOf('%s') " % team
    elif project:
        jql = "project =  '%s' " % project
    else:
        jql = "assignee = '%s' " % add_domain(user)

    return jql

def enumerate_updates(jira):
    since = datetime.datetime.now() - datetime.timedelta(days=int(cfg.args.days))

    jql = default_jql()
    jql += "AND updatedDate > -%sd" % cfg.args.days
    log.debug(jql)

    my_issues = jira.search_issues(jql, expand="changelog", fields="summary,comment,components,assignee,created")
    if my_issues.total > my_issues.maxResults:
        my_issues = jira.search_issues(jql, expand="changelog", fields="summary,comment,components,assignee,created",
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
        status['components'] = issue.fields.components

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
    since = datetime.datetime.now() - datetime.timedelta(days=7)

    jql = default_jql()
    jql += "AND status = 'In Progress' \
            AND issuetype != Initiative \
            AND issuetype != Epic"
    log.debug(jql)

    my_issues = jira.search_issues(jql, expand="changelog", fields="summary,assignee,created,components")
    if my_issues.total > my_issues.maxResults:
        my_issues = jira.search_issues(jql, expand="changelog", fields="summary,assignee,created,components",
                                       maxResults=my_issues.total)

    for issue in my_issues:
        status = {}
        status['issue'] = str(issue)
        if issue.fields.assignee:
            status['assignee'] = issue.fields.assignee.displayName
        else:
            status['assignee'] = 'Unassigned'
        status['summary'] = issue.fields.summary
        status['components'] = issue.fields.components

        created = datetime.datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z')
        status['new'] = created.replace(tzinfo=None) > since

        yield(status)

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to update comments in Jira')

    parser.add_argument('--test', required=False, action="store_true", \
            default=False, \
            help='Use the test server')

    parser.add_argument('-u', '--user', required=False, action="store", \
            default=None, \
            help='Query Jira with another Jira username \
            (first.last or first.last@linaro.org)')

    parser.add_argument('-p', '--project', required=False, action="store", \
            default=None, \
            type = str.upper, \
            help='Query Jira for only a specifc project')

    parser.add_argument('-t', '--team', required=False, action="store", \
            default=None, \
            type = str.lower, \
            help='Query Jira for only issues assigned to members of a specific tema (eg. linaro-landing-team-qualcomm)')

    parser.add_argument('--days', required=False, action="store", \
            default=7, \
            help='Period of the report in days')

    parser.add_argument('--html', required=False, nargs='?', action="store", \
            const='status.html', \
            help='Store output to HTML file')

    parser.add_argument('-v', required=False, action="store_true", \
            default=False, \
            help='Output some verbose debugging info')

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

################################################################################
# Template for outout
################################################################################
output = """
{%- for assignee in assignees %}
{{assignee}}:
{%- for issue in updates | selectattr('assignee', 'equalto', assignee) | list %}
{%- if loop.index == 1 %}
 * Past
{%- endif %}
   * [{{issue['issue']}}]{% if issue['components'] |length > 0 %} [{{issue['components']|join(',')}}]{% endif %} {{issue['summary']}} {% if issue['resolution'] %}- was {{issue['resolution']|lower}}{% endif %}
  {%- for c in issue['comments'] %}
    {%- for cc in c.splitlines() %}
    {% if loop.index == 1 %} *{% else %}  {% endif %} {{cc}}
    {%- endfor %}
  {%- endfor %}
{%- endfor %}
{%- for issue in pendings | selectattr('assignee', 'equalto', assignee) | list %}
{%- if loop.index == 1 %}
 * Ongoing
{%- endif %}
   * [{{issue['issue']}}]{% if issue['components'] |length > 0 %} [{{issue['components']|join(',')}}]{% endif %} {{issue['summary']}}
 {%- endfor %}
{% endfor %}
"""

output_html = """
<html>
<body>
{%- for assignee in assignees %}
{{assignee}}:
<ul>
{%- for issue in updates | selectattr('assignee', 'equalto', assignee) | list %}
{%- if loop.index == 1 %}
<li>Past</li>
    <ul>
{%- endif %}
        <li>[<a href="{{url}}/browse/{{issue['issue']}}">{{issue['issue']}}</a>]{% if issue['components'] |length > 0 %} [{{issue['components']|join(',')}}]{% endif %} {{issue['summary']}} {% if issue['resolution'] %} - was {{issue['resolution']|lower}}{% endif %}</li>
        {%- for c in issue['comments'] %}
        {%- if loop.index == 1 %}
            <ul>
        {%- endif %}
                <li>{{'<br>'.join(c.splitlines())}}</li>
        {%- if loop.index == loop.length %}
            </ul>
        {%- endif %}
        {%- endfor %}
{%- if loop.index == loop.length %}
    </ul>
{%- endif %}
{%- endfor %}
{%- for issue in pendings | selectattr('assignee', 'equalto', assignee) | list %}
{%- if loop.index == 1 %}
<li>Ongoing</li>
    <ul>
{%- endif %}
        <li>[<a href="{{url}}/browse/{{issue['issue']}}">{{issue['issue']}}</a>]{% if issue['components'] |length > 0 %} [{{issue['components']|join(',')}}]{% endif %} {{issue['summary']}}</li>
{%- if loop.index == loop.length %}
    </ul>
{%- endif %}
{%- endfor %}
</ul>
{% endfor %}
</body>
</html>
"""

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

    jira, username = jiralogin.get_jira_instance(cfg.args.test)

    if cfg.args.user is None:
        cfg.args.user = username

    updates = list(enumerate_updates(jira))
    pendings = list(enumerate_pending(jira))

    assignees = sorted(set([u['assignee'] for u in updates]) | set([p['assignee'] for p in pendings]))
    # Move "Unassigned" issues to the end
    assignees.sort(key='Unassigned'.__eq__)

    template = Template(output)
    print(template.render(assignees=assignees, updates=updates, pendings=pendings, url=jira.client_info()))

    if cfg.args.html:
        f = open(cfg.args.html, 'w')
        template = Template(output_html)
        f.write(template.render(assignees=assignees, updates=updates, pendings=pendings, url=jira.client_info()))
        f.close()

if __name__ == "__main__":
    main()
