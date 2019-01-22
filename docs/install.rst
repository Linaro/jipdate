.. _install:

#########################
Installation instructions
#########################
.. todo::

    Video: 

First step is to get the required packages, here we are using ``apt-get`` for
package management (Debian, Ubuntu etc). Then you need to clone Jipdate itself
and then finally install all the needed Python packages.

.. note::

    Jipdate is **Python3** only! So at line 2 (*python3-pip*) and 5 (*pip3*) you
    have to adjust accordingly. I.e., if Python3 is default on your distro, then
    it might be that the package is simply ``python-pip``. The important message
    is that you **only** use Jipdate with Python3!

.. code-block:: bash
    :linenos:
    :emphasize-lines: 2, 5

    $ sudo apt update && sudo apt upgrade
    $ sudo apt install python3-pip git
    $ git clone https://github.com/Linaro/jipdate.git
    $ cd jipdate
    $ pip3 install --user -r requirements.txt 
