import logging as log
import os
import sys
import yaml

TEST_SERVER = { 'url' : 'https://dev-projects.linaro.org' }
PRODUCTION_SERVER = { 'url' : 'https://projects.linaro.org' }

args = None

# Config file paths and name, basically we allow the user to store the
# .config.yml/config.yml in either the application directory, the $HOME
# directory or the  $HOME/.config/jipdate directory.
config_app_dir = sys.path[0]
config_home_config_dir = os.environ['HOME'] + "/.config/jipdate"
config_home_dir = os.environ['HOME']
config_locations = [config_app_dir, config_home_dir, config_home_config_dir]
config_path = config_home_config_dir

# Config filenames
config_filename = ".jipdate.yml"
config_legacy_filename = "config.yml"

# Config current file, will be set when initiate the config
config_file = None

yml_config = None


################################################################################
# Global config file used by different scripts
################################################################################
def create_default_config():
    """ Creates a default YAML config file for use with jipdate (default
    location is $HOME/.config/jipdate """
    yml_cfg = """# Config file for jipdate
# For use in future (backwards compatibility)
version: 1

# Jira server information
#server:
#  url: https://linaro.atlassian.net
#  token: abcdefghijkl

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
    global config_path
    global config_filename

    if not os.path.exists(config_path):
        os.makedirs(config_path)
    with open(config_path + "/" + config_filename, 'w') as f:
        f.write(yml_cfg)


def get_config_file():
    """ Returns the location for the config file (including the path). """
    global config_locations
    global config_legacy_filename
    global config_path
    global config_filename

    for d in config_locations:
        for f in [config_filename, config_legacy_filename]:
            checked_file = d + "/" + f
            if os.path.isfile(checked_file):
                return d + "/" + f

    # If nothing was found, then return the default file
    return config_path + "/" + config_filename


def get_server(use_test_server=False):
    # Get Jira Server details. Check first if using the test server
    # then try user config file, then default from cfg.py
    server = TEST_SERVER
    if use_test_server is False:
        server = yml_config.get('server', PRODUCTION_SERVER)

    return server


def initiate_config():
    """ Reads the config file (yaml format) and returns the sets the global
    instance.
    """
    global yml_config
    global config_file

    config_file = get_config_file()
    if not os.path.isfile(config_file):
        create_default_config()

    log.debug("Using config file: %s" % config_file)
    with open(config_file, 'r') as yml:
        yml_config = yaml.load(yml, Loader=yaml.FullLoader)
