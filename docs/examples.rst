.. _jipdate_examples:

########
Examples
########
On this page you will find a list of examples of things that a Jipdate user
might want to do. It should be noted that this is not a complete list, but will
probably list the use cases that are most commonly used.c. Likewise each and
every combination of flags are not listed here. But you can of course mix flags
to include, exclude Jira tickets and so on.

.. contents:: Table of Contents

Update tickets
==============

I want to update only my Epics
------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -e


I want to update my Initiatives and Epics
-----------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q


I want to update all my tickets (Initiatives, Epics, Stories, Sub tasks)
------------------------------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q --all


I want to update only my Epics and reuse my previous comment(s)
---------------------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -e -l

Here it's the ``-l`` that makes the difference and Jipdate will pull the last
comment from the ticket(s) and include that in each section for each and every
Jira ticket assigned to you.

I want to update my Initiatives and Epics and reuse my previous comment(s)
--------------------------------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -l

Here it's the ``-l`` that makes the difference and Jipdate will pull the last
comment from the ticket(s) and include that in each section for each and every
Jira ticket assigned to you.


Updates with status reports
===========================

I want to update my Epics and create a status report
----------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -e -f status_report_week_xy.txt

When the script has finished running you will have a file
``status_report_week_xy.txt`` in the folder with your entire status update ready
to be sent out via email, for archiving or copy/pasted into a combined status
document.

.. note::

    Updating like this with the ``-q`` (query) will overwrite the file you have
    specified.


I want to update my issues based on my own status file
------------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -f my_status.txt

The use case here is that you have a Jipdate status file stored locally that you
update on regular basis and you basically never query Jira itself.


Special use cases
=================

I want to see what tickets person firstname.lastname are working with
---------------------------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -u john.doe

.. note::

    For this you still need to enter your own password even though you make a
    query about another user.


I want to see the last updates on tickets assigned to firstname.lastname
------------------------------------------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -u john.doe -l

.. note::

    For this you still need to enter your own password even though you make a
    query about another user.


I only want to print my status to stdout
----------------------------------------
.. todo::

    Video: 

.. code-block:: bash

    $ ./jipdate.py -q -p

This can be combined with other flags (e.g. ``--all``, ``-e`` etc).

Testing / development
=====================


I want to use a test-server / sandbox
-------------------------------------
.. code-block:: bash

    $ ./jipdate.py -t -q

Here we provide ``-t`` which will use Linaro's `test server`_ instead of the
real Jira instance. This is totally safe to use when playing around and testing
Jipdate. You can of course combine this with all other parameters.


I want to do a dry-run
----------------------
.. code-block:: bash

    $ ./jipdate.py -q --dry-run

With ``--dry-run`` you can query the real Jira instance without risking to make
any updates. I.e., this can be used as a complement to query the `test server`_.

I want to see more debugging text from Jipdate
----------------------------------------------
.. code-block:: bash

    $ ./jipdate.py -q -v


.. _test server: https://dev-projects.linaro.org
