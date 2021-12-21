.. _tooltip-mixin:

===============
Widget tooltips
===============

Using the ``TooltipMixin`` allows you to add a tooltip to any widget. This is
best illustrated with a simple example:

.. code:: python

    from libqtile.widget import TextBox

    from qtile_extras.widget.mixins import TooltipMixin


    class TooltipTextBox(TextBox, TooltipMixin):

        def __init__(self, *args, **kwargs):
            TextBox.__init__(self, *args, **kwargs)
            TooltipMixin.__init__(self, **kwargs)
            self.add_defaults(TooltipMixin.defaults)

            # The tooltip text is set in the following variable
            self.tooltip_text = "Tooltip message goes here..."

    # Add an instance of TooltipTextBox to your bar
    # e.g. TooltipTextBox("This space available for rent.")

When you hover your mouse over the widget you will see a message appear after a short
delay:

.. image:: /_static/images/tooltip_example.png

See the :ref:`reference page <mixins>` for instructions on how to customise the mixin.
