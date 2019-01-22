.. _issues:

Problems
========
The :ref:`install` has been tested on a brand new and clean docker instance
running Ubuntu, so it *should* work. Having that said, software is software and
people are using different tools, distros etc. Below is a set of issues that
people have seen (and that still can be seen).

.. _captcha_error:

CAPTCHA error
-------------
If you login using **wrong** credentials and the authentication has failed a
certain number of times, then the Jira server will lock down and there isn't an
easy way to reset it, other than successfully logging it via the web interface
(or having IT reset the error count.)

When that happens you typically will see a message like this:

.. code-block:: none

    JIRA - please go to JIRA using your web browser, log out of JIRA, log back
    in entering the captcha; after that is done, please re-run the script.


.. _unicodeencodeerror:

UnicodeEncodeError
------------------
Typically you will see an error message similar to this:

.. code-block:: python

    UnicodeEncodeError: 'ascii' codec can't encode character '\xa0' in position
    57: ordinal not in range(128)

We have smoked out quite a few of those, but it still shows up from time to
time. If you see them, please just file a bug at GitHub (or try to fix it and
send at patch). Please submit issues at `GitHub Jipdate Issues`_. The reason for
that error message is that there are non ASCII characters in either the Jira
ticket itself or in the users username (e.g. `Josè Doe`).

.. _GitHub Jipdate Issues: https://github.com/Linaro/jipdate/issues
