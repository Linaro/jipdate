import os
import getpass
import logging as log
import sys

from jipdate import cfg
from jira import JIRA
from jira import JIRAError

def get_username_from_config():
    """ Get the username for Jira from the config file. """
    username = None
    # First check if the username is in the config file.
    try:
        username = cfg.yml_config['username']
    except:
        log.debug("username not set in config")

    return username


def get_username_from_env():
    """ Get the username for Jira from the environment variable. """
    username = None
    try:
        username = os.environ['JIRA_USERNAME']
    except KeyError:
        log.debug("JIRA_USERNAME environment variable not set")

    return username


def get_username_from_input():
    """ Get the username for Jira from terminal. """
    username = input("Username (john.doe@foo.org): ").lower().strip()
    if len(username) == 0:
        log.error("Empty username not allowed")
        sys.exit(os.EX_NOUSER)
    else:
        return username


def store_username_in_config(username):
    """ Append the username to the config file. """
    # Needs global variable or arg instead.
    with open(cfg.config_file, 'a') as f:
        f.write("\nusername: %s" % username)


def get_username():
    """ Main function to get the username from various places. """
    username = get_username_from_env() or \
               get_username_from_config()

    if username is not None:
        return username

    username = get_username_from_input()

    if username is not None:
        question = "Username not found in %s, want to store it? (y/n) " % \
                        cfg.config_file
        answer = input(question).lower().strip()
        if answer in set(['y']):
            store_username_in_config(username)
        return username
    else:
        log.error("No JIRA_USERNAME exported and no username found in config.yml")
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
        log.debug("Forgot to export JIRA_PASSWORD?")

    password = getpass.getpass()
    if len(password) == 0:
        log.error("JIRA_PASSWORD not exported or empty password provided")
        sys.exit(os.EX_NOPERM)

    return password


def get_jira_instance(use_test_server):
    """
    Makes a connection to the Jira server and returns the Jira instance to the
    caller.
    """
    username = get_username()

    server = cfg.get_server(use_test_server)
    url = server.get('url')
    token = server.get('token')

    # password based authentication
    if not token:
        password = get_password()

    try:
        if token:
            log.debug("Accessing %s with %s using token based authentication" % (url, username))
            j = JIRA(url, basic_auth=(username, token)), username
        else:
            log.debug("Accessing %s with %s using password based authentication" % (url, username))
            j = JIRA(url, basic_auth=(username, password)), username
    except JIRAError as e:
        if e.text.find('CAPTCHA_CHALLENGE') != -1:
            log.error('Captcha verification has been triggered by '\
                   'JIRA - please go to JIRA using your web '\
                   'browser, log out of JIRA, log back in '\
                   'entering the captcha; after that is done, '\
                   'please re-run the script')
            sys.exit(os.EX_NOPERM)
        else:
            raise
    return j
