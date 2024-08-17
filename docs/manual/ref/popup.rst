.. _ref-popup-toolkit:

=============
Popup Toolkit
=============

.. _ref-popup-layouts:

Popup Toolkit Layouts
=====================

Layouts are the container that houses all the controls. In order to give the greatest
flexibility to users, there are a number of different layouts available in the toolkit.

.. qtile_module:: qtile_extras.popup.toolkit
    :baseclass: qtile_extras.popup.toolkit._PopupLayout
    :exclude-base:
    :no-commands:
    :show-config:
    :methods: show,hide,unhide,kill,update_controls,bind_callbacks


.. _ref-popup-controls:

Popup Toolkit Controls
======================

Controls are the building blocks for your popup. You can place text, images and progress bars
and have each of these react to input events or display information dynamically.

.. qtile_module:: qtile_extras.popup.toolkit
    :baseclass: qtile_extras.popup.toolkit._PopupWidget
    :exclude-base:
    :no-commands:
    :show-config: