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

# Local files
import cfg
from helper import vprint, eprint
import jiralogin

################################################################################
# Helper functions
################################################################################
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

    call(editor.split() + [filename])


def open_file(filename):
    """
    This will open the user provided file and if there has not been any file
    provided it will create and open a temporary file instead.
    """
    vprint("filename: %s\n" % filename)
    if filename:
        return open(filename, "w")
    else:
        return tempfile.NamedTemporaryFile(mode='w+t', delete=False)


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
def update_jira(jira, i, c, t):
    """
    This is the function that do the actual updates to Jira and in this case it
    is adding comments to a certain issue.
    """
    if t:
        vprint("Updating Jira issue: %s with transition: %s" % (i, t))
        jira.transition_issue(i, t)

    if c != "":
        vprint("Updating Jira issue: %s with comment:" % i)
        vprint("-- 8< --------------------------------------------------------------------------")
        vprint("%s" % c)
        vprint("-- >8 --------------------------------------------------------------------------\n\n")
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
    exclude_stories = cfg.args.x
    epics_only = cfg.args.e
    all_status = cfg.args.all
    filename = cfg.args.file
    user = cfg.args.user
    last_comment = cfg.args.l

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
    subject = "Subject: [Weekly] Week ending " + showdate + "\n\n"

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
    while True:
        target = ""
        if cfg.server == cfg.PRODUCTION_SERVER:
            target = "OFFICIAL!"
        elif cfg.server == cfg.TEST_SERVER:
            target = "TEST"

        print("Server to update: %s" % target)
        print(" %s\n" % cfg.server);
        answer = input("Are you sure you want to update Jira with the " +
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

    # Regexp to mach a tag that indicates to stop processing completely:
    # [FIN]
    regex_fin = r"^\[FIN\]\n$"

    # Regexp to match for a status update:
    regex_status = r"^Status: (.+)\n$"

    # Contains the status text, it could be a file or a status email
    status = ""

    with open(filename) as f:
        status = f.readlines()

    myissue = "";
    mycomment = "";

    # build list of {issue,comment} tuples found in status
    issue_comments = []
    for line in status:
        # New issue?
        match = re.search(regex, line)
        if match:
            myissue = match.group(1)
            validissue = True

            try:
                issue = jira.issue(myissue)
                issue_comments.append((issue, "", ""))
            except  Exception as e:
                if 'Issue Does Not Exist' in e.text:
                    print('[{}] :  {}'.format(myissue, e.text))
                    validissue = False

        # Stop parsing entirely.  This needs to be placed before regex_stop
        # or the .* will match and [FIN] won't be processed
        elif re.search(regex_fin, line):
            break
        # If we have non-JIRA issue tags, stop parsing until we find a valid tag
        elif re.search(regex_stop, line):
                validissue = False
        elif re.search(regex_status, line):
            transition = line[8:].strip()
            (i,c,_) = issue_comments[-1]
            issue_comments[-1] = (i, c, transition)
        else:
            # Don't add lines with comments
            if (line[0] != "#" and issue_comments and validissue):
                (i,c,t) = issue_comments[-1]
                issue_comments[-1] = (i, c + line, t)

    issue_upload = []
    print("These JIRA cards will be updated as follows:\n")
    for (idx,t) in enumerate(issue_comments):
        (issue,comment,transition) = issue_comments[idx]

        # Strip beginning  and trailing blank lines
        comment = comment.strip('\n')

        if transition != "" and transition != str(issue.fields.status):
            transition_map = dict([(t['name'], t['id']) for t in jira.transitions(issue)])
            if not transition in transition_map:
                print("Invalid transition \"{}\" for issue {}".format(transition, issue))
                sys.exit(1)

            transition_id = transition_map[transition]
            transition_summary = " %s => %s" % (issue.fields.status, transition)
        else:
            transition_id = None
            transition_summary = ""

        if comment == "" and not transition_id:
            vprint("Issue [%s] has no comment or transitions, not updating the issue" % (issue))
            continue

        issue_upload.append((issue, comment, transition_id))
        print("[%s]%s\n  %s" % (issue, transition_summary, "\n  ".join(comment.splitlines())))
    print("")

    issue_comments = issue_upload
    if issue_comments == [] or cfg.args.dry_run or should_update() == "n":
        if issue_comments == []:
            print("No change, Jira was not updated!\n")
        else:
            print("Comments will not be written to Jira!\n")
        if not cfg.args.s:
            print_status(status)
        sys.exit()

    # if we found something, let's update jira
    for (issue,comment,transition) in issue_comments:
        update_jira(jira, issue, comment, transition)

    print("Successfully updated your Jira tickets!\n")
    if not cfg.args.s:
        print_status(status)

def print_status_file(filename):
    with open(filename, 'r') as f:
        print(f.read())

################################################################################
# Yaml
################################################################################


def get_extra_comments():
    """ Read the jipdate config file and return all option comments. """
    try:
        yml_iter = cfg.yml_config['comments']
    except:
        # Probably no "comments" section in the yml-file.
        return "\n"

    return ("\n".join(yml_iter) + "\n") if yml_iter is not None else "\n"

def get_header():
    """ Read the jipdate config file and return all option header. """
    try:
        yml_iter = cfg.yml_config['header']
    except:
        # Probably no "comments" section in the yml-file.
        return ""

    return ("\n".join(yml_iter) + "\n\n") if yml_iter is not None else "\n"


def merge_issue_header():
    """ Read the configuration flag which decides if the issue and issue header
    shall be combined. """
    try:
        yml_iter = cfg.yml_config['use_combined_issue_header']
    except:
        # Probably no "use_combined_issue_header" section in the yml-file.
        return False
    return yml_iter


def get_header_separator():
    """ Read the separator from the jipdate config file. """
    try:
        yml_iter = cfg.yml_config['separator']
    except:
        # Probably no "separator" section in the yml-file.
        return " | "
    return yml_iter


def get_editor():
    """ Read the configuration flag that will decide whether to show the text
    editor by default or not. """
    try:
        yml_iter = cfg.yml_config['text-editor']
    except:
        # Probably no "text-editor" section in the yml-file.
        return True
    return yml_iter

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

    if not cfg.args.file and not cfg.args.q:
        eprint("No file provided and not in query mode\n")
        parser.print_help()
        sys.exit(os.EX_USAGE)

    jira, username = jiralogin.get_jira_instance(cfg.args.t)

    if cfg.args.x or cfg.args.e:
        if not cfg.args.q:
            eprint("Arguments '-x' and '-e' can only be used together with '-q'")
            sys.exit(os.EX_USAGE)

    if cfg.args.p and not cfg.args.q:
        eprint("Arguments '-p' can only be used together with '-q'")
        sys.exit(os.EX_USAGE)

    if cfg.args.q:
        filename = get_jira_issues(jira, username)

        if cfg.args.p:
            print_status_file(filename)
            sys.exit(os.EX_OK)
    elif cfg.args.file is not None:
        filename = cfg.args.file
    else:
        eprint("Trying to run script with unsupported configuration. Try using --help.")
        sys.exit(os.EX_USAGE)

    if get_editor():
        open_editor(filename)
    parse_status_file(jira, filename)

if __name__ == "__main__":
    main(sys.argv)
