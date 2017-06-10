# Jira comment updater

## Parameters to the script

```
usage: jipdate.py [-h] [-e] [-f FILE] [-l] [-p] [-q] [-t] [-u USER] [-v] [-x]
                  [--all]

Script used to update comments in Jira

optional arguments:
  -h, --help            show this help message and exit
  -e                    Only include epics (no initiatives or stories). Used
                        in combination with "-q"
  -f FILE, --file FILE  Load status update from FILE. NOTE: -q will overwrite
                        the content of FILE
  -l                    Get the last comment from Jira
  -p                    Print to stdout
  -q                    Query Jira for issue(s) assigned to you
  -s                    Be silent, only show jira updates and not entire
                        status file
  -t                    Use the test server
  -u USER, --user USER  Query Jira with another Jira username (first.last or
                        first.last@linaro.org)
  -v                    Output some verbose debugging info
  -x                    EXCLUDE stories from gathered Jira issues. Used in
                        combination with "-q"
  --all                 Load all Jira issues, not just the once marked in
                        progress.
```

## Installation
#### 1. Clone this git
```bash
$ git clone https://github.com/Linaro/jipdate.git
```

alternatively download it directly to a folder in your `$PATH`, for example:
```bash
$ cd $HOME/bin
$ wget https://raw.githubusercontent.com/Linaro/jipdate/master/jipdate.py
```

#### 2. Get the Jira and YAML package for Python
```bash
$ cd <jipdate>
$ pip install --user -r requirements.txt
```

**Note** On recent MAC OS X you may have to run
```bash
$ cd <jipdate>
$ pip install --user --upgrade -r requirements.txt
```

In case you have both Python 2 and Python 3 installed at the same machine you
will eventually need to run with `pip2` instead.
```bash
$ cd <jipdate>
$ pip2 install --user -r requirements.txt
```

**Note**, the script relies on running Python 2, and not Python 3.  If you are
using Arch Linux you may have to manually tweak the script to execute
`/usr/bin/env python2` instead.

## Jira server
The script by default uses the **official** Linaro Jira server. If you intend to
play around with the script just for testing purposes, then you **should** use
the `-t` argument, which will make the script use the Linaro **test** Jira
server instead.

## Status file
A status file could be seen as a simple text file containing a header which
could be written as a normal email. This is then followed by one or more
issue/comment sections. The idea is that you should be able to use the same file
regardless if you are just updating Jira or if you want to send it as a status
update to your team via email for example.

An example of a status update file (generated by the script itself) could look
like this:
```ini
Hi,

This is the status update from me for the last week.

Cheers!
Joakim Bech

[SWG-23]
# Header: Kernel Hardening
# Type: Initiative
# Status: In Progress
No updates since last week.

[SWG-18]
# Header: GlobalPlatform adaptations
# Type: Initiative
# Status: In Progress
No updates since last week.

[SWG-1]
# Header: TEE/TrustZone: Open Source Trusted OS
# Type: Initiative
# Status: In Progress
Maintenance still ongoing.

```
The parsing rules are rather simple.
* Lines containing **only** `[...]` with no leading or trailing white space or
  other characters are considered **tags**.
* A tag beginning with a jira issue key such as `[ISSUE-123]` marks the start
  for a new issue.  Everything after that will be considered as a comment
  belonging to that particular issue until it finds another tag
  containing for example `[ISSUE-124]` (since that marks the start for another
  new comment to another issue), or until it meets a tag, which doesn't match
  the format of a JIRA tag, such as `[STOP]` or `[OTHER]`, for example.
* Lines starting with `#` are **editor comments** and will not be included in
  the actual update message (i.e., the same way as git deals with comments in
  commit messages).  Comments can also be embedded inside a JIRA tag, for
  example writing `[ISSUE-124 # My important JIRA issue title]`.
* Everything **before** the first `[ISSUE-123]` in a status file will be ignored
  when updating Jira. Instead that will typically be used to write additional
  information complementing the status update when re-using the status file to
  send email about your status.  This information can alse come after the JIRA
  issue updates, as long as a tag without a valid JIRA issue key tells the
  script to stop processing text, for example by inserting a tag such as
  `[STOP]` or `[OTHER]` (see above).
* It is possible to refer to other issues in a comment as long as it is not
  standalone on a single line, i.e., in a comment section it is fine to write that
  "This depends on `[ISSUE-111]`".

## Run the script
With command line parameters, there several ways to run the script. But the three
most common cases are listed here below (section 2-4). Pick the one that suites
your needs best, but first, start with exporting your credentials to the Jira
server.
#### 1. Export your credentials in your shell
```bash
$ export JIRA_USERNAME="john.doe@linaro.org"
$ export JIRA_PASSWORD="my-super-secret-password"
```
We know that this isn't best practice when it comes to security. In bash you can
play with `HISTCONTROL` to make bash not save the information in the history
file. In many configurations it is sufficient to add a leading space before the
export command to make bash not save a command to history.

#### 2. Create/update a status file
If you have no previous status file, then the easiest way to is to make the
script create one for you, this is done by (generates a file similar to the one
above in the previous section):
```bash
$ ./jipdate.py -q -f status.txt
```

or if want **all** of your open issues, then run:
```bash
$ ./jipdate.py -q --all -f status.txt
```

**Note** that when using the `-f` parameter in combination with `-q` will make
the script overwrite the current file. If you **do not** want to override the
file, then look at the next section(s).

#### 3. Use a status file without query Jira
If you **do not** want the script to override you status file then you **should
not** use the `-q` parameter when running the script. An example when this could
be used is when you already have a file containing almost up-to-date information
and you only want to make minor modifications to it. I.e, it could be that you
re-use the same file week after week. So, in this case you simply run the script
by:
```bash
$ ./jipdate.py -f status.txt
```

#### 4. Do not use any local file
As an alternative to working with a local file, you can simply call the script
without using the `-f` parameter. In that case it will simply use the output
from the Jira query (in a temporary file). Here is how to do that:
```bash
$ ./jipdate.py -q
```

or if want **all** of your open issues, then run:
```bash
$ ./jipdate.py -q --all
```

## Known bugs
* Works on Python2 only (probably an easy fix, raw_input / input must be fixed).
