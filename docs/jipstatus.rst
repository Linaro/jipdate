.. _jipstatus_examples:

##################
Jipstatus Examples
##################

On this page you will find a list of examples of things that a Jipdate user
might want to do with the `jipstatus` command. It should be noted that this is
not a complete list, but will probably list the use cases that are most commonly
used.c.

.. contents:: Table of Contents

Retrieve my updates
===================

I want to retrieve all my updates
---------------------------------

The default behavior for `jipstatus` when no specific arguments are used is to
query the Jira server for all the updates for the current user in the last
week.

.. code-block:: bash

    $ ./jipstatus.py

The `--days` argument can be used to query for any arbitrary duration (in days):

.. code-block:: bash

    $ ./jipstatus.py --days 30

I want to generate an HTML output
---------------------------------

The argument `--html` can be used to generate a report in HTML format. By
default `jipstatus` will create the file `status.html`, which can be changed by
the user:

.. code-block:: bash

    $ ./jipstatus.py --html [file.html]

Retrieve updates for a specific Jira project
============================================

Instead of querying Jira for a specific user, `--project` can be used to request
updates to all tickets from a specific project.

.. code-block:: bash

    $ ./jipstatus.py --project <PJT_KEY>

Several arguments can be combined together:

.. code-block:: bash

    $ ./jipstatus.py --project <PJT_KEY> --days 30 --html

Retrieve updates for a specific Jira team
=========================================

The `--team` argument can be used to retrieve updates from all users who belong
to a specific Jira team (or group):

.. code-block:: bash

    $ ./jipstatus.py --team linaro --days 30 --html


Retrieve updates for a specific Jira user
=========================================

The `--user` argument can be used to retrieve update from a specific user, it
can be the user email address, or the short form firstname.lastname.

.. code-block:: bash

    $ ./jipstatus.py --user jane.doe --days 30 --html


I want to see more debugging text from Jipstatus
================================================

You can use `-v` to request verbose output.

.. code-block:: bash

    $ ./jipstatus.py -v
