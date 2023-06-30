#!/usr/bin/env python3
from argparse import ArgumentParser
from argparse import FileType
import logging as log
import re
import os
import sys
import yaml
from dateutil import parser
from jira import JIRAError

# Local files
from jipdate import cfg
from jipdate import jiralogin
from jipdate import __version__


################################################################################
# Argument parser
################################################################################
def get_parser():
    """Takes care of script argument parsing."""
    parser = ArgumentParser(description="Script used to search tickets in Jira")

    parser.add_argument(
        "-u",
        "--user",
        required=False,
        action="store",
        default=None,
        help="""Query Jira with another Jira username
            (first.last or first.last@linaro.org)""",
    )

    parser.add_argument(
        "-o",
        "--outputfile",
        required=False,
        action="store",
        default=sys.stdout,
        type=FileType("w"),
        dest="output",
        help="Directs the output to a name of your choice",
    )

    parser.add_argument(
        "-j",
        "--jql",
        required=False,
        action="append",
        default=None,
        help="""JQL string to query Jira. Can be specified several
            times to allow several searches being displayed in the search result.""",
    )

    parser.add_argument(
        "-p",
        "--project",
        required=False,
        action="store",
        default=None,
        help="""Define which project to search in.
            Separate with comma to search in several projects""",
    )

    parser.add_argument(
        "-r",
        "--reporter",
        required=False,
        action="store",
        default=None,
        help="""Search for issues with the specified reporters.
            Use comma to separate multiple reporters.""",
    )

    parser.add_argument(
        "-a",
        "--assignee",
        required=False,
        action="append",
        default=None,
        help="""Search for issues with the specified assignees.""",
    )

    parser.add_argument(
        "-e",
        "--epic",
        required=False,
        action="store",
        default=None,
        help="""Epic with children, specify epic to view with children.""",
    )

    parser.add_argument(
        "-ca",
        "--created-after",
        required=False,
        action="store",
        default=None,
        help="""Search for issues created after this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".""",
    )

    parser.add_argument(
        "-cb",
        "--created-before",
        required=False,
        action="store",
        default=None,
        help="""Search for issues created before this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".""",
    )

    parser.add_argument(
        "-ua",
        "--updated-after",
        required=False,
        action="store",
        default=None,
        help="""Search for issues updated after this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".""",
    )

    parser.add_argument(
        "-ub",
        "--updated-before",
        required=False,
        action="store",
        default=None,
        help="""Search for issues updated before this date and time.
            Valid formats include: "yyyy/MM/dd HH:mm", "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd", "yyyy-MM-dd", or a period format e.g. "-5d", "4w 2d".""",
    )

    parser.add_argument(
        "-d",
        "--description",
        required=False,
        action="store_true",
        default=False,
        help="""View description.""",
    )

    parser.add_argument(
        "-c",
        "--comments",
        required=False,
        action="store_true",
        default=False,
        help="""View latest comments.""",
    )

    parser.add_argument(
        "-f",
        "--format",
        required=False,
        action="store",
        default=None,
        help="""Print in user's format string.
        Example string:
        --format 'Issue {key}, Parent issue: {parent:key}, Issue assignee email: {assignee:emailAddress}'""",
    )

    parser.add_argument(
        "-k",
        "--key",
        required=False,
        action="append",
        default=None,
        help="""Show information about a specific Epic/Story/Task.""",
    )

    parser.add_argument(
        "-pk",
        "--parent",
        required=False,
        action="store_true",
        default=False,
        help="""print parent key if available.""",
    )

    parser.add_argument(
        "-s",
        "--sprint",
        required=False,
        action="store",
        default=None,
        help="""Show Story/Task in sprint.""",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        default=False,
        help="""Output some verbose debugging info""",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s, {__version__}"
    )

    parser.add_argument(
        "--dry-run",
        required=False,
        action="store_true",
        default=False,
        help="""Do not make any changes to JIRA""",
    )

    return parser


def initialize_logger(args):
    LOG_FMT = "[%(levelname)s] %(funcName)s():%(lineno)d   %(message)s"
    lvl = log.ERROR
    if args.verbose:
        lvl = log.DEBUG

    log.basicConfig(
        # filename="core.log",
        level=lvl,
        format=LOG_FMT,
        filemode="w",
    )


def print_output(s):
    cfg.args.output.write(str(s))


def create_jql(jira, initial_jql):
    jql_parts = []
    if initial_jql and initial_jql != "":
        jql_parts.append(initial_jql)

    if cfg.args.key:
        key_parts = f"key in ({cfg.args.key[0]}"
        for v in cfg.args.key[1:]:
            key_parts += f", {v}"
        jql_parts.append(f"{key_parts})")

    if cfg.args.project:
        jql_parts.append("project in (%s)" % cfg.args.project)

    if cfg.args.sprint:
        jql_parts.append("sprint in ('%s')" % cfg.args.sprint)

    if cfg.args.reporter:
        reporter_ids = []
        reporters = cfg.args.reporter.split(",")
        for r in reporters:
            reporter_ids += jira.search_users(query=r)
        if len(reporter_ids) > 0:
            account_ids = []
            for ri in reporter_ids:
                account_ids.append(ri.accountId)
            jql_parts.append("reporter in (%s)" % ",".join(account_ids))

    if cfg.args.assignee:
        assignee_ids = []
        for r in cfg.args.assignee:
            assignee_ids += jira.search_users(query=r)
        if len(assignee_ids) > 0:
            account_ids = []
            for ai in assignee_ids:
                account_ids.append(ai.accountId)
            jql_parts.append("assignee in (%s)" % ",".join(account_ids))

    if cfg.args.epic:
        jql_parts.append(
            "(key = %s or parentepic = %s)" % (cfg.args.epic, cfg.args.epic)
        )

    if cfg.args.created_after:
        jql_parts.append("created >= %s" % cfg.args.created_after)

    if cfg.args.created_before:
        jql_parts.append("created <= %s" % cfg.args.created_before)

    if cfg.args.updated_after:
        jql_parts.append("updated >= %s" % cfg.args.updated_after)

    if cfg.args.updated_before:
        jql_parts.append("updated <= %s" % cfg.args.updated_before)

    jql_string = " AND ".join(jql_parts)

    log.debug(f"{jql_string}")
    return jql_string


def search_issues(jira, jql):
    issues = []
    result = {"startAt": 0, "total": 1}
    max_results = 50

    while result["startAt"] < result["total"]:
        fields = [
            "summary",
            "description",
            "created",
            "status",
            "issuetype",
            "assignee",
            "timetracking",
        ]

        if cfg.args.format:
            regex = r"\{(.+?)\}"
            for keys in re.findall(regex, cfg.args.format):
                fields.append(keys.split(":")[0])

        if cfg.args.parent:
            fields.append("parent")

        try:
            result = jira.search_issues(
                jql,
                startAt=result["startAt"],
                maxResults=max_results,
                fields=fields,
                json_result=True,
            )
        except JIRAError as e:
            print_output(f"{e.text}")
            exit(1)
        issues += result["issues"]
        result["startAt"] += max_results

    return issues


def call_jqls(jira, jql):
    issues = []
    for j in jql:
        jql_str = create_jql(jira, j)
        issues += search_issues(jira, jql_str)
    return issues


def print_issues(jira, issues):
    for issue in issues:
        jira_link = "https://linaro.atlassian.net/browse"
        if cfg.args.format:
            regex = r"\{(.+?)\}"
            format_line = re.sub(regex, "{}", cfg.args.format)
            out = []
            for keys in re.findall(regex, cfg.args.format):
                tmp_output = issue["fields"]
                for k in keys.split(":"):
                    if len(keys.split(":")) == 1 and "key" == k:
                        tmp_output = issue["key"]
                    elif k in tmp_output:
                        tmp_output = tmp_output[k]
                    else:
                        tmp_output = "None"
                        continue
                out.append(tmp_output)

            print_output(format_line.format(*out))
            continue
        output = f"{jira_link}/{issue['key']} , Type: {issue['fields']['issuetype']['name'].strip()}, Summary: {issue['fields']['summary'].strip()} , Created: {str(parser.parse(issue['fields']['created'])).split(' ')[0]} , Status: {issue['fields']['status']['statusCategory']['name']}"
        if issue["fields"]["assignee"]:
            assignee_ = f", Assignee: {issue['fields']['assignee']['displayName']}, Assignee email: {issue['fields']['assignee']['emailAddress']}"
            output += assignee_

        if cfg.args.parent:
            try:
                field = issue["fields"]["parent"]
                value = f" parent: {jira_link}/{field['key']}"
                print_output(f"{output},{value}")
            except KeyError:
                print_output(f"No key 'parent'.")
            continue

        print_output(f"{output}")
        if cfg.args.description:
            print_output(f"# Description:")
            descriptions = issue["fields"]["description"]
            if descriptions:
                for line in descriptions.split("\n"):
                    print_output(f"#   {line}")
                print_output(f"#\n")

        if cfg.args.comments:
            c = jira.comments(issue["key"])
            if len(c) > 0:
                try:
                    timespent = issue["fields"]["timetracking"]["timeSpent"]
                except KeyError:
                    timespent = 0
                try:
                    originalestimate = issue["fields"]["timetracking"][
                        "originalEstimate"
                    ]
                except KeyError:
                    originalestimate = "Not Set"
                print_output(
                    f"# Assignee: {issue['fields']['assignee']['displayName']}, Original Estimate: {originalestimate}, Time Spent: {timespent}"
                )
                print_output(
                    f"# Last comment, updated: {c[0].updated}, by: {c[0].author}"
                )
                comment = "# ---8<---\n# %s\n# --->8---\n" % "\n# ".join(
                    c[-1].body.splitlines()
                )
                print_output(comment)

        # print_output(f"{issue['key']}, status: {issue['fields']['status']['statusCategory']['name']}, created: {str(parser.parse(issue['fields']['created'])).split(' ')[0]}\n\t   Summary: {issue['fields']['summary']}\n\t   https://linaro.atlassian.net/browse/{issue['key']}")


################################################################################
# Main function
################################################################################
def main():
    argv = sys.argv
    parser = get_parser()
    if len(sys.argv) == 1:
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
        log.debug(f"JQL: " + jql[0])
        issues = call_jqls(jira, jql)
    else:
        issues = call_jqls(jira, [""])

    print_issues(jira, issues)


if __name__ == "__main__":
    main()
