.. _bar-borders:

===========
Bar Borders
===========

.. note::

    As of 14 November 2021, this functionality has been merged into the main Qtile repo.
    The code will remain here until the next version release of Qtile so that people can
    continue to use this repo with package releases of Qtile. After that, the code will be
    removed from this repo.

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

    If you are creating your own widget then you should take a look at :ref:`the decorations
    page <wrapping_widgets>` for details on how to inject the relevant code into your widgets.

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
