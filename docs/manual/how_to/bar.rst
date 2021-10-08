.. _bar-borders:

===========
Bar Borders
===========

.. note::

    There is an open `PR`_ in the qtile repository to add bar borders
    to the official repo. If that request is merged then the
    decorations may be removed from this repository.

.. _PR: https://github.com/qtile/qtile/pull/2675

This mod allows you to draw borders around your bar.

It's incredibly simple to use, just change the import in your config file, replacing:

.. code:: python

    from libqtile.bar import Bar

with:

.. code:: python

    from qtile_extras.bar import Bar

Configuring the bar
===================

.. important::

    If you use this mod, you must import all widgets from ``qtile_extras.widget`` as the
    mod injects code into the widgets to adjust their position.

    If you are creating your own widget then you should take a look at the source code for
    the code injection to see what changes need to be made in the widget.

The mod adds two new options to ``Bar``: ``border_color`` and ``border_width``. Both
options take a single value or a list of four values representing `top`, `right`, `bottom`
and `left` edges of the bar.

For example:

.. code:: python

    from qtile_extras import widget
    from qtile_extras.bar import Bar

    ...

    screens = [
        Screen(
            bottom=Bar(
                [
                    widget.CurrentLayoutIcon(),
                    widget.GroupBox(),
                    widget.Spacer(),
                    widget.WiFiIcon(padding=5),
                    widget.Clock(),
                    widget.ScriptExit(
                        default_text="[X]",
                        countdown_format="[{}]",
                        countdown_start=2,
                    ),
                ],
                30,
                background="000000.5",
                border_color=["990099", "000000", "990099", "000000"],
                border_width=[2, 0, 2, 0],
                margin=10
            )
        )
    ]

Gives you a bar like this:

.. figure:: /_static/images/bar.png
    :target: ../../_static/images/bar.png
