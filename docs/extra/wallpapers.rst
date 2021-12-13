Wallpapers
==========

At one point, we thought about shipping Qtile with a default wallpaper as that
would be a bit more welcoming than the current black screen. The PR met with
mixed reactions so I'll put my "artwork" here instead.

These can be added to your config by doing:

.. code:: python

    from qtile_extras.resources import wallpapers
    
    ...
    
    screens = [
        Screen(
            top=Bar(...),
            wallpaper=wallpapers.WALLPAPER_TRIANGLES,
            wallpaper_mode="fill"
        )
    ]

.. qte_wallpapers::

