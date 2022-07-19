.. _jipcreate_examples:

################
Jipcreate Examples
################

On this page you will find a list of examples of things that a Jipcreate user
might want to do. It should be noted that this is not a complete list, but will
probably list the use cases that are most commonly used. Likewise each and
every combination of keywords that can be specified in the yaml file are not
listed here. But you can of course add/remove keywords to set values in the
storey created, or remove to use the default value in the story.

.. contents:: Table of Contents

Create issue
==============

I want to create a story
------------------------------
.. todo::

    Video:

.. code-block:: bash

    $ jipcreate -f /path/to/file.yaml

Fields that can be found in the yaml file are the following.
This is an example yaml file.

.. code-block:: bash

    - IssueType: Story
      Project: LKQ
      Summary: Make LKFT work in tuxtest
      Description: |-
        Some text can be written here.
      AssigneeEmail: firstname.surname@linaro.org
      OriginalEstimate: 5h|5d|5w
      Sprint: sprint name


Required fields in the yaml file are: IssueType, Project and Summary.

Testing / development
=====================


I want to do a dry-run
----------------------
.. code-block:: bash

    $ jipcreate --dry-run

With ``--dry-run`` you can query the real Jira instance without risking to make
any updates. I.e., this can be used to see what will be sent to the `server`.

I want to see more debugging text from Jipdate
----------------------------------------------
.. code-block:: bash

    $ jipcreate -v
