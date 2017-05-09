#!/usr/bin/python2

from jira import JIRA
import json
import re
import os
import sys

# Sandbox server
server = 'https://dev-projects.linaro.org'

# Production server, comment out this in case you want to use the real server
#server = 'https://projects.linaro.org'

try:
    username = os.environ['JIRA_USERNAME']
    password = os.environ['JIRA_PASSWORD']
except KeyError:
    print "Forgot to export JIRA_USERNAME and JIRA_PASSWORD?"
    sys.exit()

credentials=(username, password)

jira = JIRA('https://projects.linaro.org', basic_auth=credentials)
jira = JIRA(server, basic_auth=credentials)

# Regexp to match Jira issue on a single line, i.e:
# [SWG-28]
# [LITE-32]
# etc ...
regex = r"^\[[A-Z]+-\d+\]\n$"

# Contains the status text, it could be a file or a status email
status = ""

with open("status_update.txt") as f:
    status = f.readlines()

myissue = "";
mycomment = "";

def update_jira(i, c):
    print "Updating Jira issue: %s with comment:" % i
    print "-- 8< --------------------------------------------------------------------------"
    print "%s" % c
    print "-- >8 --------------------------------------------------------------------------\n\n"
    jira.add_comment(i, c)

# State to keep track of whether we are in an issue or a comment
state = "issue"

for i in range(0, len(status)):
    line = status[i]
    # New issue?
    if re.search(regex, line):
        if state == "comment":
            update_jira(myissue, mycomment)
            state = "issue"

        myissue = line.strip();
        myissue = myissue[1:-1]
        mycomment = ""
        state = "comment"
    else:
        mycomment += line

if len(mycomment) > 0:
    update_jira(myissue, mycomment)
