qtile-extras documentation
==========================

``qtile-extras`` is a collection of mods made by elParaguayo for Qtile.

These are mods that I've made but which, for various reasons, may not end
up in the main Qtile codebase.

They're designed for me but I've shared them in case they're of interest to
anyone else.

Currently, this repo houses some :ref:`widgets <ref-widgets>` that I made as well as my
":ref:`popup toolkit <extended-popups>`" which can be used to extend
widgets or make standalone menus/launchers.

The new widgets are:

.. list_objects:: qtile_extras.widget

I've also added some "eye candy" in the form of :ref:`widget decorations
<widget-decorations>`. These decorations are available to all widgets i.e.
they can be applied to the standard Qtile widgets as well as the new widgets
here.

.. note::

    These items are made primarily for my use and are not officially supported by
    Qtile. You are most welcome to install it and I hope that you find some parts
    of is useful. However, please note, I cannot guarantee that I will continue to
    maintain certain aspects of this repo if I am no longer using them so, be warned,
    things may break!

.. important::

    This repo is designed to be installed alongside the git version of Qtile. It is
    highly recommended that you run the latest version to ensure compatibility.

    I will not maintain a version of this repo that is linked to tagged releases of
    Qtile.

.. toctree::
    :caption: Getting Started
    :maxdepth: 1
    :hidden:

    manual/install
    manual/how_to/popup
    manual/how_to/decorations

.. toctree::
    :caption: Reference
    :maxdepth: 1
    :hidden:

    manual/ref/widgets
    manual/ref/popup
    manual/ref/decorations

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
