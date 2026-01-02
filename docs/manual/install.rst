.. _install:

============
Installation
============

.. important::

    The git version of qtile-extras should only be installed alongside the git version of
    Qtile. This is because qtile-extras aims to main compatibility with the latest version.

    If you are using the tagged release version of Qtile then you should use the matching tagged
    release of qtile-extras. These are guaranteed to be compatible but you will not be able to benefit
    from new features/bugfixes unless Qtile also publishes a new release.


PyPi
====

Tagged releases of qtile-extras are available on PyPi and can be installed with
``pip install qtile-extras``.

Arch users
==========

This is the easiest option as the package is in the AUR. Using your favourite
helper, you just need to download and install the ``qtile-extras`` package (for the tagged release)
or the ``qtile-extras-git`` package (for the latest git version).

Fedora
======

There is an official package for Fedora::

    dnf install qtile-extras

pipx
====

If you've installed qtile with ``pipx`` then you can add qtile-extras to the same environment by running
``pipx inject qtile qtile-extras`` (assuming the pipx environment was called ``qtile``).

Everyone else
=============

You can use ``pip`` to install the package e.g. ``pip install --user .``.

Alternatively, you can use the ``build`` and ``installer`` modules and run:

.. code::

    python -m build --wheel
    python -m installer dist/*.whl
