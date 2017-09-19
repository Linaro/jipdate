import os
import getpass

from helper import *
from jira import JIRA
from jira import JIRAError

import cfg
import helper

def get_username_from_config():
    """ Get the username for Jira from the config file. """
    username = None
    # First check if the username is in the config file.
    try:
        username = cfg.yml_config['username']
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
        answer = raw_input(question).lower().strip()
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
    username = get_username()
    password = get_password()

    credentials=(username, password)

    if use_test_server:
        cfg.server = cfg.TEST_SERVER

    try:
        j = JIRA(cfg.server, basic_auth=credentials), username
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
