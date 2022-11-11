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

I have no current intentions to package this on PyPi. This means
installation may be a bit more "manual" than for other packages.

Arch users
==========

This is the easiest option as the package is in the AUR. Using your favourite
helper, you just need to download and install the ``qtile-extras`` package (for the tagged release)
or the ``qtile-extras-git`` package (for the latest git version).

Fedora
======

There is no official package for Fedora yet but you can install it
from `Copr`_::

    dnf copr enable frostyx/qtile
    dnf install qtile-extras

.. _Copr: https://copr.fedorainfracloud.org/

Everyone else
=============

Clone the repo and run ``python setup.py install``.

