.. _border-decorations:

=========================
Window Border Decorations
=========================

.. warning::

    This feature is experimental.

    The decorations may behave unexpectedly, have missing features and will
    probably crash at some point!

    Feedback on any issues would be appreciated.

Window border decorations provide the ability to have different style borders
rather than the standard single, solid colour borders.

The following decorations are available:

.. list_objects:: qtile_extras.layout.decorations
    :baseclass: qtile_extras.layout.decorations.borders._BorderStyle

Using the decorations is simple:

.. code:: python

    from qtile_extras.layout.decorations import GradientBorder

    ...

    layouts = [
        layout.Max(
            border_width=10,
            margin=5,
            border_focus=GradientBorder(colours=["00f", "0ff"])
        ),
        ...
    ]

Results in a window looking like this:

.. image:: /_static/images/max_gradient_border.png

See :ref:`this page<ref-borders>` for details of the various borders available.

.. important::

    You must import the decorations from ``qtile_extras.layout.decorations`` as importing
    this file will add a hook to inject the code needed to allow qtile to render these
    borders.
