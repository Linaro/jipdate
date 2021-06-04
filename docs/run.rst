.. _run_jipdate:

#########################
Run Jipdate
#########################
The most straight forward way is to simply run the script

.. code-block:: bash

    $ ./jipdate

Running it without any parameters (or with ``-h``) will give you a list of all
parameters. If you want to see examples of how to combine flags/parameters, then
head over to :ref:`jipdate_examples`.

#########################
Run Jipstatus
#########################
The most straight forward way is to simply run the script

.. code-block:: bash

    $ ./jipstatus

Running it without any parameters will show all tickets updates for the current
user in the last 7 days, including newly created tickets, state transitions, and
all updates.

Running with ``-h`` will give you a list of all parameters. If you want to see
examples of how to combine flags/parameters, then head over to
:ref:`jipstatus_examples`.

Environment variables
=====================
You can export both the password and the username with environment variables and
thereby avoid having to enter them every time you run Jipdate.

.. code-block:: bash

    $ export JIRA_USERNAME="john.doe@linaro.org"
    $ export JIRA_PASSWORD="my-super-secret-password"

.. warning::
    By exporting ``JIRA_PASSWORD`` there is a chance that the password end up in
    the history of your shell (bash, zsh etc).

The same can be achieved by storing the credentials in :ref:`username` and
:ref:`password` in the :ref:`config_file`.
