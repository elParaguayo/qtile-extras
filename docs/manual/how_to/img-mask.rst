.. _img-mask:

==========
Image Mask
==========

This is a new image class that allows you provide a source image to use as a mask.
Painting with a colour then renders that colour in unmasked areas. The advantage of
this is that the colour can be set dynamically without having to preload different
images.

The example below shows a simple widget using this class to display three icons.

.. code:: python

    from libqtile import bar
    from libqtile.widget.base import _Widget

    from qtile_extras.images import ImgMask

    ICON_PATH = "/path/to/icon_folder"

    class MaskWidget(_Widget):
        def __init__(self):
            _Widget.__init__(self, bar.CALCULATED)

        def _configure(self, qtile, bar):
            _Widget._configure(self, qtile, bar)
            self.img = ImgMask.from_path(f"{ICON_PATH}/icon.svg")
            self.img.attach_drawer(self.drawer)
            self.img.resize(self.bar.height - 1)

        def calculate_length(self):
            if not self.configured:
                return 0

            return self.img.width * 3

        def draw(self):
            self.drawer.clear(self.background or self.bar.background)
            offset = 0
            for col in [
                "ff0000",
                "00ff00",
                ["ff00ff", "0000ff", "00ff00", "ff0000", "ffff00"]
            ]:
                self.img.draw(colour=col, x=offset)
                offset += self.img.width

            self.draw_at_default_position()

Placing an instance of ``MaskWidget()`` in your bar will then give you something like this:

.. figure:: /_static/images/imgmask.png

    Note you can use gradients too.

.. note::

    It is important that the ``ImgMask`` object has a reference to the widget's ``drawer`` attribute.
    In the example above, this is achieved via the call to ``self.img.attach_drawer(self.drawer)``.

Batch Loader
============

If you want to use the ``Loader`` class to load a batch of images to use as masks, you can do
that as follows (note the use of the ``masked=True`` keyword argument):

.. code:: python

    from qtile_extras.images import Loader

    image_dict = Loader(IMAGE_FOLDER, masked=True)(*IMAGE_NAMES)


As above, the images will need to have the widget's ``drawer`` object attached.
