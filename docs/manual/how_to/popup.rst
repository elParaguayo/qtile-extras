.. _extended-popups:

=======================
Using the Popup Toolkit
=======================

This guide explains how to create popups that can be used to add functionality
to widgets or create standalone launchers.

What's in the toolkit?
======================

The Toolkit has two types of object, a layout and a control. The layout is the
container that helps organise the presentation of the popup. The controls are the
objects that display the content.

A simple comparison would be to think of the ``Bar`` as the layout and widgets as the
controls. However, a key difference of this toolkit is that the controls can be placed
anywhere in a 2D space whereas widgets can only be ordered in one dimension.

Layouts
=======

The toolkit provides three layouts: ``PopupGridLayout``, ``PopupRelativeLayout`` and
``PopupAbsoluteLayout``.

Descriptions and configuration options of these layouts can be found on
:ref:`the reference page <ref-popup-layouts>`.

Controls
========

Currently, the following controls are provided:

- ``PopupText``: a simple text display object
- ``PopupImage``: a control to display an image
- ``PopupSlider``: a control to draw a line which marks a particular value (e.g. volume level)
- ``PopupWidget``: a control to display a Qtile widget in the popup

Configuration options for these controls can be found on
:ref:`the reference page <ref-popup-controls>`.

Callbacks
=========

To add functionality to your popup, you need to bind callbacks to the individual controls. 
This is achieved in the same way as widgets i.e. a dictionary of ``mouse_callbacks`` is passed
as a configuration option for the control. The control accepts any callable function but also
accepts ``lazy`` objects like those used for key bindings.

Building a popup menu
=====================

Below is an example of creating a power menu in your ``config.py``.

.. code:: python

    from qtile_extras.popup.toolkit import (
        PopupRelativeLayout,
        PopupImage,
        PopupText 
    )

    def show_power_menu(qtile):

        controls = [
            PopupImage(
                filename="~/Pictures/icons/lock.svg",
                pos_x=0.15,
                pos_y=0.1,
                width=0.1,
                height=0.5,
                mouse_callbacks={
                    "Button1": lazy.spawn("/path/to/lock_cmd")
                }
            ),
            PopupImage(
                filename="~/Pictures/icons/sleep.svg",
                pos_x=0.45,
                pos_y=0.1,
                width=0.1,
                height=0.5,
                mouse_callbacks={
                    "Button1": lazy.spawn("/path/to/sleep_cmd")
                }
            ),
            PopupImage(
                filename="~/Pictures/icons/shutdown.svg",
                pos_x=0.75,
                pos_y=0.1,
                width=0.1,
                height=0.5,
                highlight="A00000",
                mouse_callbacks={
                    "Button1": lazy.shutdown()
                }
            ),
            PopupText(
                text="Lock",
                pos_x=0.1,
                pos_y=0.7,
                width=0.2,
                height=0.2,
                h_align="center"
            ),
            PopupText(
                text="Sleep",
                pos_x=0.4,
                pos_y=0.7,
                width=0.2,
                height=0.2,
                h_align="center"
            ),
            PopupText(
                text="Shutdown",
                pos_x=0.7,
                pos_y=0.7,
                width=0.2,
                height=0.2,
                h_align="center"
            ),        
        ]

        layout = PopupRelativeLayout(
            qtile,
            width=1000,
            height=200,
            controls=controls,
            background="00000060",
            initial_focus=None,
        )

        layout.show(centered=True)

    keys = [
        ...
        Key([mod, "shift"], "q", lazy.function(show_power_menu))
        ...
    ]

Now, when you press ``Mod+shift+q`` you should see a menu looking like this:

.. image:: /_static/images/powermenu.png


Using widgets in a popup
========================

It is possible to display widgets in a popup window and not just in the bar. This is possible by using
the ``PopupWidget`` control.

Below is a quick example for displaying a number of graph widgets in a popup:

.. code:: python

    from libqtile import widget
    from qtile_extras.popup.toolkit import (
        PopupRelativeLayout,
        PopupWidget
    )

    def show_graphs(qtile)
        controls = [
            PopupWidget(
                widget=widget.CPUGraph(),
                width=0.45,
                height=0.45,
                pos_x=0.05,
                pos_y=0.05
            ),
            tk.PopupWidget(
                widget=widget.NetGraph(),
                width=0.45,
                height=0.45,
                pos_x=0.5,
                pos_y=0.05
            ),
            tk.PopupWidget(
                widget=widget.MemoryGraph(),
                width=0.9,
                height=0.45,
                pos_x=0.05,
                pos_y=0.5
            )
        ]

        layout = tk.PopupRelativeLayout(
            qtile,
            width=1000,
            height=200,
            controls=controls,
            background="00000060",
            initial_focus=None,
            close_on_click=False
        )
        layout.show(centered=True)

    keys = [
        ...
        Key([mod, "shift"], "g", lazy.function(show_graphs))
        ...
    ]

Pressing ``Mod+shift+g`` will present a popup window looking like this:

.. image:: /_static/images/popupgraphs.png

Updating controls
=================

There may be times when you wish to update the contents of the popup without
having to rebuild the whole popup. This is possible by using the
``popup.update_controls`` method. The method works by taking the name of the
control (as set by the ``name`` parameter) as a keyword. Multiple controls can
be updated in the same call.

.. code:: python

    text_popup = None

    def create_text_popup(qtile):
        global text_popup
        text_popup = tk.PopupRelativeLayout(
            qtile,
            width=400,
            height=200,
            controls=[
                tk.PopupText(
                    text="Original Text",
                    width=0.9,
                    height=0.9,
                    pos_x=0.05,
                    pos_y=0.05,
                    v_align="middle",
                    h_align="center",
                    fontsize=20,
                    name="textbox1"
                ),
            ],
            inital_focus=None,
            close_on_click=False,
        )

        text_popup.show(centered=True)

    def update_text_popup(qtile):
        text_popup.update_controls(textbox1="Updated Text")

Extending widgets
=================

[To be drafted]
