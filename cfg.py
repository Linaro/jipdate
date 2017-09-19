import os
import sys

TEST_SERVER = 'https://dev-projects.linaro.org'
PRODUCTION_SERVER = 'https://projects.linaro.org'
server = PRODUCTION_SERVER

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
