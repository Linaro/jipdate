# Jira comment updater

## Parameters to the script

```
usage: jipdate.py [-h] [-q] [-e] [-f FILE] [-t] [-v] [-x] [--all]

Script used to update comments in Jira

optional arguments:
  -h, --help            show this help message and exit
  -q                    Query Jira for issue(s) assigned to you
  -e                    Only include epics (no initiatives or stories). Used
                        in combination with "-c"
  -f FILE, --file FILE  file to use containing a status update(s)
  -t                    Use the test server
  -v                    Output some verbose debugging info
  -x                    EXCLUDE stories from gathered Jira issues. Used in
                        combination with "-c"
  --all                 Load all Jira issues, not just the once marked in
                        progress.
```

## Installation
### 1. Clone this git
```bash
$ git clone https://github.com/jbech-linaro/jipdate.git
```

alternatively download it directly to a folder in your `$PATH`, for example:
```bash
$ cd $HOME/bin
$ wget https://raw.githubusercontent.com/jbech-linaro/jipdate/master/jipdate.py
```

### 2. Get the Jira package for Python
```bash
$ sudo pip install jira
```

**Note** On recent MAC OS X you may have to run
```bash
$ sudo  pip install --user --upgrade jira
```

In case you have both Python 2 and Python 3 installed at the same machine you
will eventually need to run with `pip2` instead.
```bash
$ sudo pip2 install jira
```

## Run the script
### 1. Create or update the status_update.txt file
The `status_update.txt` file should contain single or multiple issues with a
comment. So the format is:

**[issue]** <- Single line, no spaces, no indents, no spaces after the word.

**comment ...** <- Can be any text, spaces, newlines etc, it can even include
other [issues] as long as they are not standalone on a single row (as described
above).

Example of `status_update.txt` containing a single comment.
```
[SWG-25]
This is my superduper comment

It can contain empty lines        many space, and even references
to other issues like [LHG-52].
```

You can add **multiple** issues and comments in one go also, example:

```
[SWG-25]
This is my superduper comment

It can contain empty lines        many space, and even references
to other issues like [LHG-52].

[SWG-26]
This issue is currently blocked.

But we intend to work with it after issue [SWG-200].

[SWG-27]
No updates this week
```

You can also **start** the status file with any text. It will simply ignore that
until it finds the first single row matching **[issue]**, example:

```
Hi all!

This is my status update for this week.

// Take care
Joakim


[SWG-25]
This is my superduper comment

It can contain empty lines        many space, and even references
to other issues like [LHG-52].

[SWG-26]
This issue is currently blocked.

But we intend to work with it after issue [SWG-200].

[SWG-27]
No updates this week
```

### 2. Export your credentials in your shell
```bash
$ export JIRA_USERNAME="john.doe@linaro.org"
$ export JIRA_PASSWORD="my-super-secret-password"
```

### 3. Update Jira!
Simply run the script (with the different arguments)
```bash
$ ./jipdate.py
```
or if you have the script in the `$PATH`
```bash
$ jipdate.py
```

**Note**, the script is by default configured to use the **official** Jira
server. If you intend to just test the script without affecting the official
Jira server, then you shall use the `-t` parameter.

**Note**, the script relies on running Python 2, and not Python 3.  If you're
using Arch Linux you may have to manually tweak the script to execute
'/usr/bin/env python2' instead.
