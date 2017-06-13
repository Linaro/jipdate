#!/usr/bin/env python

from __future__ import print_function

from argparse import ArgumentParser
from jira import JIRA
from jira import JIRAError
from subprocess import call
from time import gmtime, strftime

import getpass
import json
import os
import re
import sys
import sys
import tempfile
import yaml

TEST_SERVER = 'https://dev-projects.linaro.org'
PRODUCTION_SERVER = 'https://projects.linaro.org'

# Global variables
g_config_file = None
g_config_filename = "config.yml"
g_server = PRODUCTION_SERVER
g_args = None

# Yaml instance, opened at the beginning of main and then kept available
# globally.
g_yml_config = None

################################################################################
# Helper functions
################################################################################
def eprint(*args, **kwargs):
    """ Helper function that prints on stderr. """
    print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs):
    """ Helper function that prints when verbose has been enabled. """
    global g_args
    if g_args.v:
        print(*args, file=sys.stdout, **kwargs)


def print_status(status):
    """ Helper function printing your status """
    print("This is your status:")
    print("\n---\n")
    print("\n".join(l.strip('\n') for l in status))


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
    elif os.path.exists("/usr/bin/vi"):
        editor = "/usr/bin/vi"
    else:
        eprint("Could not load an editor.  Please define EDITOR or VISUAL")
        sys.exit(os.EX_CONFIG)

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

    parser.add_argument('-e', required=False, action="store_true", \
            default=False, \
            help='Only include epics (no initiatives or stories). Used in combination \
            with "-q"')

    parser.add_argument('-f', '--file', required=False, action="store", \
            default=None, \
            help='Load status update from FILE.  NOTE: -q will overwrite the \
            content of FILE')

    parser.add_argument('-l', required=False, action="store_true", \
            default=False, \
            help='Get the last comment from Jira')

    parser.add_argument('-p', required=False, action="store_true", \
            default=False, \
            help='Print Jira query result to stdout (no editor or jira updates)')

    parser.add_argument('-q', required=False, action="store_true", \
            default=False, \
            help='Query Jira for issue(s) assigned to you')

    parser.add_argument('-s', required=False, action="store_true", \
            default=False, \
            help='Be silent, only show jira updates and not entire status file')

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

    parser.add_argument('--dry-run', required=False, action="store_true", \
            default=False, \
            help='Do not make any changes to JIRA')

    return parser

################################################################################
# Jira functions
################################################################################
def update_jira(jira, i, c):
    """
    This is the function that do the actual updates to Jira and in this case it
    is adding comments to a certain issue.
    """
    global g_args

    vprint("Updating Jira issue: %s with comment:" % i)
    vprint("-- 8< --------------------------------------------------------------------------")
    vprint("%s" % c)
    vprint("-- >8 --------------------------------------------------------------------------\n\n")
    if not g_args.dry_run:
        jira.add_comment(i, c)


def write_last_jira_comment(f, jira, issue):
    """ Pulls the last comment from Jira from an issue and writes it to the file
    object.
    """
    c = jira.comments(issue)
    if len(c) > 0:
        try:
            comment = "# Last comment:\n# ---8<---\n# %s\n# --->8---\n" % \
                        "\n# ".join(c[-1].body.splitlines())
            f.write(comment)
        except UnicodeEncodeError:
            vprint("Can't encode character")


def get_jira_issues(jira, username):
    """
    Query Jira and then creates a status update file (either temporary or named)
    containing all information found from the JQL query.
    """
    global g_args

    exclude_stories = g_args.x
    epics_only = g_args.e
    all_status = g_args.all
    filename = g_args.file
    user = g_args.user
    last_comment = g_args.l

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

    showdate = strftime("%Y-%m-%d", gmtime())
    subject = "# Subject: [Weekly] Week ending " + showdate + "\n\n"

    msg = get_header()
    if msg != "":
        msg += email_to_name(username) + "\n\n"

    f = open_file(filename)
    filename = f.name

    f.write(subject)

    f.write(msg)
    vprint("Found issue:")
    for issue in my_issues:
        vprint("%s : %s" % (issue, issue.fields.summary))

        if (merge_issue_header()):
            f.write("[%s%s%s]\n" % (issue, get_header_separator(), issue.fields.summary))
        else:
            f.write("[%s]\n" % issue)
            f.write("# Header: %s\n" % issue.fields.summary)

        f.write("# Type: %s\n" % issue.fields.issuetype)
        f.write("# Status: %s\n" % issue.fields.status)
        f.write(get_extra_comments())
        if last_comment:
            write_last_jira_comment(f, jira, issue)
        f.write("\n")

    f.close()
    return filename


def should_update():
    """ A yes or no dialogue. """
    global g_server
    while True:
        target = ""
        if g_server == PRODUCTION_SERVER:
            target = "OFFICIAL!"
        elif g_server == TEST_SERVER:
            target = "TEST"

        print("Server to update: %s" % target)
        print(" %s\n" % g_server);
        answer = raw_input("Are you sure you want to update Jira with the " +
                           "information above? [y/n] ").lower().strip()
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
    global g_args

    # Regexp to match Jira issue on a single line, i.e:
    # [SWG-28]
    # [LITE-32]
    # ...
    regex = r"^\[([A-Z]+-[0-9]+).*\]\n$"

    # Regexp to match a tag that indicates we should stop processing, ex:
    # [STOP]
    # [JIPDATE-STOP]
    # [OTHER]
    # ...
    regex_stop = r"^\[.*\]\n$"

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
        # If we have non-JIRA issue tags, stop parsing until we find a valid tag
        elif re.search(regex_stop, line):
                validissue = False
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
        comment = comment.strip('\n')

        if comment == "":
            vprint("Issue [%s] has no comment, not updating the issue" % (issue))
            continue

        issue_upload.append((issue, comment))
        print("[%s]\n  %s" % (issue, "\n  ".join(comment.splitlines())))
    print("")

    issue_comments = issue_upload
    if issue_comments == [] or g_args.dry_run or should_update() == "n":
        if issue_comments == []:
            print("No change, Jira was not updated!\n")
        else:
            print("Comments will not be written to Jira!\n")
        if not g_args.s:
            print_status(status)
        sys.exit()

    # if we found something, let's update jira
    for (issue,comment) in issue_comments:
        update_jira(jira, issue, comment)

    print("Successfully updated your Jira tickets!\n")
    if not g_args.s:
        print_status(status)

def print_status_file(filename):
    with open(filename, 'r') as f:
        print(f.read())

def get_username_from_config():
    """ Get the username for Jira from the config file. """
    username = None
    # First check if the username is in the config file.
    try:
        username = g_yml_config['username']
    except:
        vprint("No username found in config")

    return username

def get_username_from_env():
    """ Get the username for Jira from the environment variable. """
    username = None
    try:
        username = os.environ['JIRA_USERNAME']
    except KeyError:
        vprint("No user name found in JIRA_USERNAME environment variable")

    return username

def get_username_from_input():
    """ Get the username for Jira from terminal. """
    username = raw_input("Username (john.doe@foo.org): ").lower().strip()
    if len(username) == 0:
        eprint("Empty username not allowed")
        sys.exit(os.EX_NOUSER)
    else:
        return username


def store_username_in_config(username):
    """ Append the username to the config file. """
    # Needs global variable or arg instead.
    config_file = "config.yml"
    with open(config_file, 'a') as f:
        f.write("\nusername: %s" % username)


def get_username():
    """ Main function to get the username from various places. """
    username = get_username_from_env() or \
               get_username_from_config()

    if username is not None:
        return username

    username = get_username_from_input()

    if username is not None:
        answer = raw_input("Username not found in config.yml, want to store " + \
                           "it? (y/n) ").lower().strip()
        if answer in set(['y']):
            store_username_in_config(username)
        return username
    else:
        eprint("No JIRA_USERNAME exported and no username found in config.yml")
        sys.exit(os.EX_NOUSER)


def get_password():
    """
    Get the password either from the environment variable or from the
    terminal.
    """
    try:
        password = os.environ['JIRA_PASSWORD']
        return password
    except KeyError:
        vprint("Forgot to export JIRA_PASSWORD?")

    password = getpass.getpass()
    if len(password) == 0:
        eprint("JIRA_PASSWORD not exported or empty password provided")
        sys.exit(os.EX_NOPERM)

    return password


def get_jira_instance(use_test_server):
    """
    Makes a connection to the Jira server and returns the Jira instance to the
    caller.
    """
    global g_server
    username = get_username()
    password = get_password()

    credentials=(username, password)

    if use_test_server:
        g_server = TEST_SERVER

    try:
        j = JIRA(g_server, basic_auth=credentials), username
    except JIRAError, e:
	if e.text.find('CAPTCHA_CHALLENGE') != -1:
            eprint('Captcha verification has been triggered by '\
                   'JIRA - please go to JIRA using your web '\
                   'browser, log out of JIRA, log back in '\
                   'entering the captcha; after that is done, '\
                   'please re-run the script')
            sys.exit(os.EX_NOPERM)
        else:
            raise
    return j

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

          Cheers!

# Set this to 'True' if you want to get the issue header merged with the issue
# number.
use_combined_issue_header: False

# Default separator in the issue header, change to the separator of your own
# preference.
separator: ' | '
text-editor: True"""

    with open(config_file, 'w') as f:
        f.write(yml_cfg)


def initiate_config(config_file):
    """ Reads the config file (yaml format) and returns the sets the global
    instance.
    """
    global g_yml_config

    if not os.path.isfile(config_file):
        create_default_config(config_file)

    with open(config_file, 'r') as yml:
        g_yml_config = yaml.load(yml)


def get_extra_comments():
    """ Read the jipdate config file and return all option comments. """
    global g_yml_config
    try:
        yml_iter = g_yml_config['comments']
    except:
        # Probably no "comments" section in the yml-file.
        return "\n"

    return ("\n".join(yml_iter) + "\n") if yml_iter is not None else "\n"

def get_header():
    """ Read the jipdate config file and return all option header. """
    global g_yml_config
    try:
        yml_iter = g_yml_config['header']
    except:
        # Probably no "comments" section in the yml-file.
        return ""

    return ("\n".join(yml_iter) + "\n\n") if yml_iter is not None else "\n"


def merge_issue_header():
    """ Read the configuration flag which decides if the issue and issue header
    shall be combined. """
    global g_yml_config
    try:
        yml_iter = g_yml_config['use_combined_issue_header']
    except:
        # Probably no "use_combined_issue_header" section in the yml-file.
        return False
    return yml_iter


def get_header_separator():
    """ Read the separator from the jipdate config file. """
    global g_yml_config
    try:
        yml_iter = g_yml_config['separator']
    except:
        # Probably no "separator" section in the yml-file.
        return " | "
    return yml_iter


def get_editor():
    """ Read the configuration flag that will decide whether to show the text
    editor by default or not. """
    global g_yml_config

    try:
        yml_iter = g_yml_config['text-editor']
    except:
        # Probably no "text-editor" section in the yml-file.
        return True
    return yml_iter

################################################################################
# Main function
################################################################################
def main(argv):
    global g_args
    global g_yml_config
    global g_config_filename

    # This initiates the global yml configuration instance so it will be
    # accessible everywhere after this call.
    initiate_config(g_config_filename)

    parser = get_parser()

    # The parser arguments are accessible everywhere after this call.
    g_args = parser.parse_args()

    if not g_args.file and not g_args.q:
        eprint("No file provided and not in query mode\n")
        parser.print_help()
        sys.exit(os.EX_USAGE)

    jira, username = get_jira_instance(g_args.t)

    if g_args.x or g_args.e:
        if not g_args.q:
            eprint("Arguments '-x' and '-e' can only be used together with '-q'")
            sys.exit(os.EX_USAGE)

    if g_args.p and not g_args.q:
        eprint("Arguments '-p' can only be used together with '-q'")
        sys.exit(os.EX_USAGE)

    if g_args.q:
        filename = get_jira_issues(jira, username)

        if g_args.p:
            print_status_file(filename)
            sys.exit(os.EX_OK)
    elif g_args.file is not None:
        filename = g_args.file
    else:
        eprint("Trying to run script with unsupported configuration. Try using --help.")
        sys.exit(os.EX_USAGE)

    if get_editor():
        open_editor(filename)
    parse_status_file(jira, filename)

if __name__ == "__main__":
    main(sys.argv)
