#!/usr/bin/env python

from __future__ import print_function
import json
import os
import re
import sys
import tempfile
from argparse import ArgumentParser
from jira import JIRA
from subprocess import call
import sys

# Sandbox server
server = 'https://dev-projects.linaro.org'

# Production server, comment out this in case you want to use the real server
#server = 'https://projects.linaro.org'

DEFAULT_FILE = "status_update.txt"

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def get_args():
    parser = ArgumentParser(description='Script used to update comments in Jira')

    parser.add_argument('-c', required=False, action="store_true", \
            default=False, \
            help='Gather all Jira issue(s) assigned to you into the \
            status_update.txt file')

    parser.add_argument('-e', required=False, action="store_true", \
            default=False, \
            help='Use the EDITOR instead of the status_update.txt file')

    parser.add_argument('-x', required=False, action="store_true", \
            default=False, \
            help='Enabling this flag will EXCLUDE stories. Used in combination \
            with "-c"')

    return parser.parse_args()

################################################################################

def get_my_name():
    n = os.environ['JIRA_USERNAME'].split("@")[0].title()
    return n.replace(".", " ")

################################################################################

def update_jira(jira, i, c):
    print("Updating Jira issue: %s with comment:" % i)
    print("-- 8< --------------------------------------------------------------------------")
    print("%s" % c)
    print("-- >8 --------------------------------------------------------------------------\n\n")
    jira.add_comment(i, c)

################################################################################

message_header = """Hi,

This is the status update from me for the last week.

Cheers!
"""

def get_jira_issues(jira, exclude_stories, use_editor):
    global DEFAULT_FILE

    issue_type = "issuetype in (Epic, Initiative"
    if not exclude_stories:
        issue_type = issue_type + ", Story"
    issue_type = issue_type + ") AND "

    jql = issue_type + "assignee = currentUser() AND status not in (Resolved, Closed)"
    my_issues = jira.search_issues(jql)
    msg = message_header + get_my_name() + "\n\n"

    if use_editor:
        f = tempfile.NamedTemporaryFile(delete=False)
    else:
        f = open(DEFAULT_FILE, "w")

    DEFAULT_FILE = f.name

    f.write(msg)
    print("Found issue:")
    for issue in my_issues:
        print("%s : %s" % (issue, issue.fields.summary))
        f.write("[%s]\n" % issue)
        f.write("# Header: %s\n" % issue.fields.summary)
        f.write("# Type: %s\n" % issue.fields.issuetype)
        f.write("# Status: %s\n" % issue.fields.status)
        f.write("No updates since last week.\n\n")

    if not use_editor:
        print("\n" + DEFAULT_FILE + " has been prepared with all of your open\n" + \
              "issues. Manually edit the file, then re-run this script without\n" + \
              "the '-c' parameter to update your issues.")
    f.close()

################################################################################
def should_update():
    while True:
        answer = raw_input("Sure you want to update Jira with the information " +
                           "above? [y/n] ").lower().strip()
        if answer in set(['y', 'n']):
            return answer
        else:
            print("Incorrect input: %s" % answer)

################################################################################
def open_editor(filename):
    if "EDITOR" in os.environ:
        editor = os.environ['EDITOR']
    elif "VISUAL" in os.environ:
        editor = os.environ['VISUAL']
    elif os.path.exists("/usr/bin/editor"):
        editor = "/usr/bin/editor"
    elif os.path.exists("/usr/bin/vim"):
        editor = "/usr/bin/vim"
    else:
        eprint("Could not load an editor.  Please define EDITOR or VISAUL")
        sys.exit()

    call([editor, DEFAULT_FILE])

################################################################################
def parse_status_file(jira, filename):
    # Regexp to match Jira issue on a single line, i.e:
    # [SWG-28]
    # [LITE-32]
    # etc ...
    regex = r"^\[([A-Z]+-\d+)\]\n$"

    # Contains the status text, it could be a file or a status email
    status = ""

    with open(DEFAULT_FILE) as f:
        status = f.readlines()

    myissue = "";
    mycomment = "";

    print("Information to update is as follows:")
    print("================================================================================")
    for l in status:
        print(l.strip())
    print("================================================================================")

    if should_update() == "n":
        print("No change, nothing has been updated!")
        sys.exit()

    # State to keep track of whether we are in an issue or a comment
    state = "issue"

    for line in status:
        # New issue?
        match = re.search(regex, line)
        if match:
            if state == "comment":
                update_jira(jira, myissue, mycomment)
                state = "issue"

            myissue = match.group(1)
            mycomment = ""
            state = "comment"
        else:
            # Don't add lines with comments
            if (line[0] != "#"):
                mycomment += line

    if len(mycomment) > 0:
        update_jira(jira, myissue, mycomment)

    print("Successfully updated your Jira tickets!")


################################################################################
def main(argv):
    args = get_args()
    try:
        username = os.environ['JIRA_USERNAME']
        password = os.environ['JIRA_PASSWORD']
    except KeyError:
        eprint("Forgot to export JIRA_USERNAME and JIRA_PASSWORD?")
        sys.exit()

    credentials=(username, password)
    jira = JIRA(server, basic_auth=credentials)

    exclude_stories = False
    if args.x:
        if not args.c:
            eprint("Parameter '-x' can only be used together with '-c'")
            sys.exit()
        exclude_stories = True

    if args.c:
        get_jira_issues(jira, exclude_stories, args.e)
        # Only continue if we run directly in the editor
        if not args.e:
            sys.exit()
        else:
            open_editor(DEFAULT_FILE)

    parse_status_file(jira, DEFAULT_FILE)


if __name__ == "__main__":
        main(sys.argv)
