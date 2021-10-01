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
        log.error("Could not load an editor.  Please define EDITOR or VISUAL")
        sys.exit(os.EX_CONFIG)

    call(editor.split() + [filename])


def open_file(filename):
    """
    This will open the user provided file and if there has not been any file
    provided it will create and open a temporary file instead.
    """
    log.debug("filename: %s\n" % filename)
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
            help='EXCLUDE stories and sub-tasks from gathered Jira issues. Used in combination \
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
    if t['transition']:
        if t['resolution']:
            log.debug("Updating Jira issue: %s with transition: %s (%s)" %
                   (i, t['transition'], t['resolution']))
            jira.transition_issue(i, t['transition'], fields={'resolution':{'id': t['resolution']}})
        else:
            log.debug("Updating Jira issue: %s with transition: %s" % (i, t['transition']))
            jira.transition_issue(i, t['transition'])

    if c != "":
        log.debug("Updating Jira issue: %s with comment:" % i)
        log.debug("-- 8< --------------------------------------------------------------------------")
        log.debug("%s" % c)
        log.debug("-- >8 --------------------------------------------------------------------------\n\n")
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
            log.debug("Can't encode character")


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

    issue_types = ["Sub-task", "Epic"]
    if not epics_only:
        issue_types.append("Initiative")
        if not exclude_stories:
            issue_types.extend(["Story", "Sub-task", "Bug"])
    issue_type = "issuetype in (%s)" % ", ".join(issue_types)

    status = "status in (\"In Progress\")"
    if all_status:
        status = "status not in (Resolved, Closed)"

    if user is None:
        user = "currentUser()"
    else:
        user = "\"%s\"" % add_domain(user)

    jql = "%s AND assignee = %s AND %s" % (issue_type, user, status)
    log.debug(jql)

    my_issues = jira.search_issues(jql)
    if my_issues.total > my_issues.maxResults:
        my_issues = jira.search_issues(jql, maxResults=my_issues.total)

    showdate = strftime("%Y-%m-%d", gmtime())
    subject = "Subject: [Weekly] Week ending " + showdate + "\n\n"

    msg = get_header()
    if msg != "":
        msg += email_to_name(username) + "\n\n"

    f = open_file(filename)
    filename = f.name

    f.write(subject)

    f.write(msg)
    log.debug("Found issue:")
    for issue in my_issues:
        log.debug("%s : %s" % (issue, issue.fields.summary))

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
    return (filename, my_issues)


def should_update():
    """ A yes or no dialogue. """
    while True:
        server = cfg.get_server()
        print("Server to update: %s\n" % server.get('url'));
        answer = input("Are you sure you want to update Jira with the " +
                           "information above? [y/n] ").lower().strip()
        if answer in set(['y', 'n']):
            return answer
        else:
            print("Incorrect input: %s" % answer)


def parse_status_file(jira, filename, issues):
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

    # Regexp to match for a status update, this will remove 'Status' from the
    # match:
    regex_status = r'(?:^Status:) *(.+)\n$'

    # Contains the status text, it could be a file or a status email
    status = ""

    # List of resolutions (when doing a transition to Resolved). Query once globally.
    resolution_map = dict([(t.name.title(), t.id) for t in jira.resolutions()])

    with open(filename) as f:
        status = f.readlines()

    myissue = "";
    mycomment = "";

    # build list of {issue,comment} tuples found in status
    issue_comments = []
    for line in status:
        # New issue?
        match = re.search(regex, line)

        # Evaluate and save the transition regex for later. We have to do this
        # here, since we cannot assign and save the variable in the if
        # construction as you can do in C for example.
        transition = re.search(regex_status, line)

        if match:
            myissue = match.group(1)
            validissue = True

            # if we ran a query, we might already have fetched the issue
            # let's try to find the issue there first, otherwise ask Jira
            try:
                issue = [x for x in issues if str(x) == myissue][0]
                issue_comments.append((issue, "", ""))

            # IndexError: we had fetched already, but issue is not found
            # TypeError: issues is None, we haven't queried Jira yet, at all
            except (IndexError, TypeError) as e:
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
        elif transition and validissue:
            # If we have a match, then the new status should be first in the
            # group. Jira always expect the name of the state transitions to be
            # word capitalized, hence the call to the title() function. This
            # means that it doesn't matter if the user enter all lower case,
            # mixed or all upper case. All of them will work.
            new_status = transition.groups()[0].title()
            (i,c,_) = issue_comments[-1]
            issue_comments[-1] = (i, c, new_status)
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

        # initialize here to avoid unassigned variables and useless code complexity
        resolution_id = transition_id = None
        resolution = transition_summary = ""

        if transition != "" and transition != str(issue.fields.status):
            # An optional 'resolution' attribute can be set when doing a transition
            # to Resolved, using the following pattern: Resolved / <resolution>
            if transition.startswith('Resolved') and '/' in transition:
                (transition, resolution) = map(str.strip, transition.split('/'))
                if not resolution in resolution_map:
                    print("Invalid resolution \"{}\" for issue {}".format(resolution, issue))
                    print("Possible resolution: {}".format([t for t in resolution_map]))
                    sys.exit(1)
                resolution_id = resolution_map[resolution]

            transition_map = dict([(t['name'].title(), t['id']) for t in jira.transitions(issue)])
            if not transition in transition_map:
                print("Invalid transition \"{}\" for issue {}".format(transition, issue))
                print("Possible transitions: {}".format([t for t in transition_map]))
                sys.exit(1)

            transition_id = transition_map[transition]
            if resolution:
                transition_summary = " %s => %s (%s)" % (issue.fields.status, transition, resolution)
            else:
                transition_summary = " %s => %s" % (issue.fields.status, transition)

        if comment == "" and not transition_id:
            log.debug("Issue [%s] has no comment or transitions, not updating the issue" % (issue))
            continue

        issue_upload.append((issue, comment,
                             {'transition': transition_id, 'resolution': resolution_id}))
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

    if not cfg.args.file and not cfg.args.q:
        log.error("No file provided and not in query mode\n")
        parser.print_help()
        sys.exit(os.EX_USAGE)

    jira, username = jiralogin.get_jira_instance(cfg.args.t)

    if cfg.args.x or cfg.args.e:
        if not cfg.args.q:
            log.error("Arguments '-x' and '-e' can only be used together with '-q'")
            sys.exit(os.EX_USAGE)

    if cfg.args.p and not cfg.args.q:
        log.error("Arguments '-p' can only be used together with '-q'")
        sys.exit(os.EX_USAGE)

    if cfg.args.q:
        (filename, issues) = get_jira_issues(jira, username)

        if cfg.args.p:
            print_status_file(filename)
            sys.exit(os.EX_OK)
    elif cfg.args.file is not None:
        filename = cfg.args.file
    else:
        log.error("Trying to run script with unsupported configuration. Try using --help.")
        sys.exit(os.EX_USAGE)

    if get_editor():
        open_editor(filename)

    try:
        issues
    # issues is not defined, we haven't made any query yet.
    except NameError:
        parse_status_file(jira, filename, None)
    else:
        parse_status_file(jira, filename, issues)

if __name__ == "__main__":
    main()
