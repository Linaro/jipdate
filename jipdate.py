#!/usr/bin/env python

from __future__ import print_function

from argparse import ArgumentParser
from jira import JIRA
from subprocess import call

import json
import os
import re
import sys
import sys
import tempfile
import yaml

TEST_SERVER = 'https://dev-projects.linaro.org'
PRODUCTION_SERVER = 'https://projects.linaro.org'
server = PRODUCTION_SERVER

# Yaml instance, opened at the beginning of main and then kept available
# globally.
yml_config = None

################################################################################
# Helper functions
################################################################################
def eprint(*args, **kwargs):
    """ Helper function that prints on stderr. """
    print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs):
    """ Helper function that prints when verbose has been enabled. """
    if verbose:
        print(*args, file=sys.stdout, **kwargs)


def print_status(status):
    """ Helper function printing your status """
    print("This is your status:")
    print("\n---\n")
    print("\n".join(l.strip() for l in status))


def open_editor(filename):
    """
    Function that tries to find the best suited editor to use and then
    opens the status file in the editor.
    """
    if "EDITOR" in os.environ:
        editor = os.environ['EDITOR']
    elif "VISUAL" in os.environ:
        editor = os.environ['VISUAL']
    elif os.path.exists("/usr/bin/editor"):
        editor = "/usr/bin/editor"
    elif os.path.exists("/usr/bin/vim"):
        editor = "/usr/bin/vim"
    else:
        eprint("Could not load an editor.  Please define EDITOR or VISUAL")
        sys.exit()

    call([editor, filename])


def open_file(filename):
    """
    This will open the user provided file and if there has not been any file
    provided it will create and open a temporary file instead.
    """
    vprint("filename: %s\n" % filename)
    if filename:
        return open(filename, "w")
    else:
        return tempfile.NamedTemporaryFile(delete=False)


def add_domain(user):
    """
    Helper function that appends @linaro.org to the username. It does nothing if
    it is already included.
    """
    if '@' not in user:
        user = user + "@linaro.org"
    return user


def email_to_name(email):
    """ Converts 'first.last@linaro.org' to 'First Last'. """
    n = email.split("@")[0].title()
    return n.replace(".", " ")

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to update comments in Jira')

    parser.add_argument('-q', required=False, action="store_true", \
            default=False, \
            help='Query Jira for issue(s) assigned to you')

    parser.add_argument('-e', required=False, action="store_true", \
            default=False, \
            help='Only include epics (no initiatives or stories). Used in combination \
            with "-q"')

    parser.add_argument('-f', '--file', required=False, action="store", \
            default=None, \
            help='Load status update from FILE.  NOTE: -q will overwrite the \
            content of FILE')

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

    parser.add_argument('-x', required=False, action="store_true", \
            default=False, \
            help='EXCLUDE stories from gathered Jira issues. Used in combination \
            with "-q"')

    parser.add_argument('--all', required=False, action="store_true", \
            default=False, \
            help='Load all Jira issues, not just the once marked in progress.')

    parser.add_argument('-p', required=False, action="store_true", \
            default=False, \
            help='Print to stdout')

    return parser

################################################################################
# Jira functions
################################################################################
def update_jira(jira, i, c):
    """
    This is the function that do the actual updates to Jira and in this case it
    is adding comments to a certain issue.
    """
    vprint("Updating Jira issue: %s with comment:" % i)
    vprint("-- 8< --------------------------------------------------------------------------")
    vprint("%s" % c)
    vprint("-- >8 --------------------------------------------------------------------------\n\n")
    jira.add_comment(i, c)

def get_jira_issues(jira, exclude_stories, epics_only, all_status, filename,
                    user):
    """
    Query Jira and then creates a status update file (either temporary or named)
    containing all information found from the JQL query.
    """
    issue_types = ["Epic"]
    if not epics_only:
        issue_types.append("Initiative")
        if not exclude_stories:
            issue_types.append("Story")
    issue_type = "issuetype in (%s)" % ", ".join(issue_types)

    status = "status in (\"In Progress\")"
    if all_status:
        status = "status not in (Resolved, Closed)"

    if user is None:
        user = "currentUser()"
    else:
        user = "\"%s\"" % add_domain(user)

    jql = "%s AND assignee = %s AND %s" % (issue_type, user, status)
    vprint(jql)

    my_issues = jira.search_issues(jql)

    msg = get_header()
    if msg != "":
        msg += email_to_name(os.environ['JIRA_USERNAME']) + "\n\n"

    f = open_file(filename)
    filename = f.name

    f.write(msg)
    vprint("Found issue:")
    for issue in my_issues:
        vprint("%s : %s" % (issue, issue.fields.summary))
        f.write("[%s]\n" % issue)
        f.write("# Header: %s\n" % issue.fields.summary)
        f.write("# Type: %s\n" % issue.fields.issuetype)
        f.write("# Status: %s\n" % issue.fields.status)
        f.write(get_extra_comments())

    f.close()
    return filename


def should_update():
    """ A yes or no dialogue. """
    global server
    while True:
        target = ""
        if server == PRODUCTION_SERVER:
            target = "OFFICAL!"
        elif server == TEST_SERVER:
            target = "TEST"

        print("Server to update: %s" % target)
        print(" %s\n" % server);
        answer = raw_input("Sure you want to update Jira with the information " +
                           "above? [y/n] ").lower().strip()
        if answer in set(['y', 'n']):
            return answer
        else:
            print("Incorrect input: %s" % answer)


def parse_status_file(jira, filename):
    """
    The main parsing function, which will decide what should go into the actual
    Jira call. This for example removes the beginning until it finds a
    standalone [ISSUE] tag. It will also remove all comments prefixed with '#'.
    """
    # Regexp to match Jira issue on a single line, i.e:
    # [SWG-28]
    # [LITE-32]
    # etc ...
    regex = r"^\[(.*)\]\n$"

    # Contains the status text, it could be a file or a status email
    status = ""

    with open(filename) as f:
        status = f.readlines()

    myissue = "";
    mycomment = "";

    # build list of {issue-key,comment} tuples found in status
    issue_comments = []
    for line in status:
        # New issue?
        match = re.search(regex, line)
        if match:
            myissue = match.group(1)
            validissue = True

            try:
                issue = jira.issue(myissue)
            except  Exception as e:
                if 'Issue Does Not Exist' in e.text:
                    print ('[{}] :  {}'.format(myissue, e.text))
                    validissue = False

            if validissue:
                issue_comments.append((myissue, ""))
        else:
            # Don't add lines with comments
            if (line[0] != "#" and issue_comments and validissue):
                (i,c) = issue_comments[-1]
                issue_comments[-1] = (i, c + line)

    issue_upload = []
    print("These JIRA cards will be updated as follows:\n")
    for (idx,t) in enumerate(issue_comments):
        (issue,comment) = issue_comments[idx]

        # Strip beginning  and trailing blank lines
        comment = comment.strip()

        if comment == "":
            vprint("Issue [%s] has no comment, not updating the issue" % (issue))
            continue

        issue_upload.append((issue, comment))
        print("[%s]\n  %s" % (issue, "\n  ".join(comment.splitlines())))
    print("")

    issue_comments = issue_upload
    if should_update() == "n":
        print("No change, Jira was not updated!\n")
        print_status(status)
        sys.exit()

    # if we found something, let's update jira
    for (issue,comment) in issue_comments:
        update_jira(jira, issue, comment)

    print("Successfully updated your Jira tickets!\n")
    print_status(status)

def print_status_file(filename):
    with open(filename, 'r') as f:
        print(f.read())

def get_jira_instance(use_test_server):
    """
    Makes a connection to the Jira server and returns the Jira instance to the
    caller.
    """
    global server

    try:
        username = os.environ['JIRA_USERNAME']
        password = os.environ['JIRA_PASSWORD']
    except KeyError:
        eprint("Forgot to export JIRA_USERNAME and JIRA_PASSWORD?")
        sys.exit()

    credentials=(username, password)

    if use_test_server:
        server = TEST_SERVER

    return JIRA(server, basic_auth=credentials)

################################################################################
# Yaml
################################################################################
def create_default_config(config_file):
    """ Creates a default YAML config file for use with jipdate. """
    yml_cfg = """# Config file for jipdate
# For use in future (backwards compatibility)
version: 1

# Extra comments added to each Jira issue (multiline is OK)
comments:
        - "# No updates since last week."

# Header of the file (multiline is OK). It will be followed by JIRA_USERNAME
header:
        - |
          Hi,

          This is the status update from me for the last week.

          Cheers!"""

    with open(config_file, 'w') as f:
        f.write(yml_cfg)


def initiate_config(config_file):
    """ Reads the config file (yaml format) and returns the sets the global
    instance.
    """
    global yml_config

    config_file = "config.yml"

    if not os.path.isfile(config_file):
        create_default_config(config_file)

    with open(config_file, 'r') as yml:
        yml_config = yaml.load(yml)


def get_extra_comments():
    """ Read the jipdate config file and return all option comments. """
    global yml_config
    try:
        yml_iter = yml_config['comments']
    except:
        # Probably no "comments" section in the yml-file.
        return "\n"

    return ("\n".join(yml_iter) + "\n\n") if yml_iter is not None else "\n"

def get_header():
    """ Read the jipdate config file and return all option header. """
    global yml_config
    try:
        yml_iter = yml_config['header']
    except:
        # Probably no "comments" section in the yml-file.
        return ""

    return ("\n".join(yml_iter) + "\n\n") if yml_iter is not None else "\n"

################################################################################
# Main function
################################################################################
def main(argv):
    global verbose
    global yml_config

    # This initiates the global yml configuration instance so it will be
    # accessible everywhere after this call.
    initiate_config("config.yml")

    parser = get_parser()
    args = parser.parse_args()

    verbose=args.v
    if not args.file and not args.q:
        eprint("No file provided and not in query mode\n")
        parser.print_help()
        sys.exit()

    jira = get_jira_instance(args.t)

    exclude_stories = args.x
    epics_only = args.e
    if args.x or args.e:
        if not args.q:
            eprint("Arguments '-x' and '-e' can only be used together with '-c'")
            sys.exit()

    if args.p and not args.q:
        eprint("Arguments '-p' can only be used together with '-q'")
        sys.exit()

    if args.q:
        filename = get_jira_issues(jira, exclude_stories, epics_only, \
                                   args.all, args.file, args.user)

        if args.p:
            print_status_file(filename)
            sys.exit()
    elif args.file is not None:
        filename = args.file
    else:
        eprint("This should not happen")

    open_editor(filename)
    parse_status_file(jira, filename)

if __name__ == "__main__":
    main(sys.argv)
