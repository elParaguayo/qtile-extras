.. _widget-decorations:

==================
Widget Decorations
==================

.. note::

    There is an open `PR`_ in the qtile repository to add widget
    decorations to the official repo. If that request is merged then the
    decorations may be removed from this repository.

.. _PR: https://github.com/qtile/qtile/pull/2489

Widget decorations are additional content that is drawn to your widget before the main content
is rendered i.e. you can add drawings behind your widgets.

Types of decoration
===================

The following decorations are available:

.. list_objects:: qtile_extras.widget.decorations
    :baseclass: qtile_extras.widget.decorations._Decoration

Adding decorations to your widgets
==================================

All widgets available from this repo can have decorations added to them.

In addition, all widgets in the main Qtile repository can also have decorations attached.
To do this, you simply need to change the import in your config file, replacing:

.. code:: python

    from libqtile import widget

with:

.. code:: python

    from qtile_extras import widget

A fuller example would look like this:

.. code:: python

    from qtile_extras import widget
    from qtile_extras.widget.decorations import RectDecoration

    decor = {
        "decorations": [
            RectDecoration(colour="#600060", radius=10, filled=True, padding_y=5)
        ],
        "padding": 18, 
    }

    screens = [
        Screen(
            bottom=bar.Bar(
                [
                    widget.GroupBox(**decor),
                    ...
                    widget.Clock(**decor),
                    widget.QuickExit(**decor),
                ]
            )
        )
    ]
