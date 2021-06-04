.. _install:

#########################
Installation instructions
#########################
First step is to get the required packages, then you need to clone Jipdate
itself and then finally install all the needed Python packages.

The video clip below will show how to install it and how to do a simple update
with state changes and adding comments to a Jira ticket. Note that you are
**not** required to run it in a Docker container. The only reason for doing that
was to try the installation from a clean system to ensure that things are
working as supposed to when starting out from scratch.

.. raw:: html

    <iframe width="560" height="315"
    src="https://www.youtube.com/embed/q8CMftA4c4M" frameborder="0"
    allow="accelerometer; autoplay; encrypted-media; gyroscope;
    picture-in-picture" allowfullscreen></iframe>

.. note::

    Jipdate is **Python3** only! So at line 2 (*python3-pip*) and 5 (*pip3*) you
    have to adjust accordingly. I.e., if Python3 is default on your distro, then
    it might be that the package is simply ``python-pip`` (like on Arch Linux
    for example). The important message is that you **only** use Jipdate with
    Python3!

Ubuntu / Debian based systems
=============================
.. code-block:: bash
    :linenos:
    :emphasize-lines: 3, 6

    $ sudo apt update 
    $ sudo apt upgrade
    $ sudo apt install python3-pip git
    $ git clone https://github.com/Linaro/jipdate.git
    $ cd jipdate
    $ pip3 install --user -r requirements.txt 

Fedora / Red Hat based systems
==============================
.. code-block:: bash
    :linenos:
    :emphasize-lines: 2, 4

    $ sudo dnf -y install python3-pyyaml python3-jira
    $ git clone https://github.com/Linaro/jipdate.git
    $ cd jipdate
    $ pip3 install --user -r requirements.txt

Arch Linux
==========
.. code-block:: bash
    :linenos:
    :emphasize-lines: 2, 5

    $ sudo pacman -Syu
    $ sudo pacman -S extra/git extra/python extra/python-pip
    $ git clone https://github.com/Linaro/jipdate.git
    $ cd jipdate
    $ pip3 install --user -r requirements.txt 
