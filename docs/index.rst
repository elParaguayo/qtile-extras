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

There's a :ref:`mixin <tooltip-mixin>` if you want to add tooltips to widgets.

I've also added some "eye candy" in the form of:

  - :ref:`Widget Decorations <widget-decorations>`
  - :ref:`Wallpapers <wallpapers>`

Lastly, I've created a new ``ImgMask`` class which, rather than drawing the source image,
uses the source as a mask for the drawing. This can be used to change the colour of icons
without needing to recrate the icons themselves. You can see the class :ref:`here <img-mask>`.

.. note::

    These items are made primarily for my use and are not officially supported by
    Qtile. You are most welcome to install it and I hope that you find some parts
    of is useful. However, please note, I cannot guarantee that I will continue to
    maintain certain aspects of this repo if I am no longer using them so, be warned,
    things may break!

.. toctree::
    :caption: Getting Started
    :maxdepth: 1
    :hidden:

    manual/install
    manual/how_to/popup
    manual/how_to/decorations
    manual/how_to/img-mask
    manual/how_to/tooltips

.. toctree::
    :caption: Reference
    :maxdepth: 1
    :hidden:

    manual/ref/widgets
    manual/ref/popup
    manual/ref/decorations
    manual/ref/imgmask

.. toctree::
    :caption: Extras
    :maxdepth: 1
    :hidden:

    extra/wallpapers

.. toctree::
    :caption: Development
    :maxdepth: 1
    :hidden:

    dev/changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
