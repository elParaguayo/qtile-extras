.. _widget-decorations:

==================
Widget Decorations
==================

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

.. _wrapping_widgets:

Adding decorations to user-defined widgets
==========================================

You can also add the ability to draw decorations to your own widgets.

If you are creating a widget than inherits from an existing widget then all you
need to do is import that widget class from ``qtile_extras.widget``. As a result, the
decoration code will already be imported.

If you are creating a new widget from scratch, there are two ways to add support for decorations:

The first, and preferred method, is to add a decorator to the class definition as follows:

.. code:: python

    from libqtile.widget.base import _TextBox

    from qtile_extras.widget import add_decoration_support

    @add_decoration_support
    class MyTextWidget(_TextBox):
        pass

Alternatively, you can import ``modify`` from ``qtile_extras.widget`` and use this to
wrap your widget class and its configuration parameters. i.e. calling ``modify(WidgetClass,
*args, **kwargs)`` will return ``WidgetClass(*args, **kwargs)``.

.. code:: python

    from libqtile.config import Screen
    from libqtile.widget.base import _TextBox

    from qtile_extras.bar import Bar
    from qtile_extras.widget import modify


    class MyTextWidget(_TextBox):
        pass

    
    screens = [
        Screen(
            bottom=Bar(
                [
                    ...
                    modify(
                        MyTextWidget,
                        text="Modded widget",
                        decorations=[
                            ...
                        ]
                    ),
                    ...
                ]
            )
        )
    ]

.. note::

    To be honest, the ``modify`` method only really exists because I didn't think about using a decorator!
    I'll leave it in the code so it doesn't break anything...
