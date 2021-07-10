# elParaguayo's Qtile Extras

This is a separate repo where I share things that I made for qtile that (probably) won't ever end up in the main repo.

This things were really just made for use by me so your mileage may vary.


## UPower Widget

This module provides a simple widget showing the status of a laptop battery.

### About

The module uses the UPower DBus interface to obtain information about the current power source.

The widget is drawn by the module rather than using icons from a theme. This allows more customisation of colours.

### Demo

Here is a screenshot showing the widget in the bar.

_Normal:_</br>
![Screenshot](images/battery_normal.png?raw=true)

_Low:_</br>
![Screenshot](images/battery_low.png?raw=true)

_Critical:_</br>
![Screenshot](images/battery_critical.png?raw=true)

_Charging:_</br>
![Screenshot](images/battery_charging.png?raw=true)

_Multiple batteries:_</br>
![Screenshot](images/battery_multiple.png?raw=true)

_Showing text:_</br>
![Screenshot](images/battery_textdisplay.gif?raw=true)

### Configuration

Add the code to your config (`~/.config/qtile/config.py`):

```python
from qtile_extras import widget as extrawidgets
...
screens = [
    Screen(
        top=bar.Bar(
            [
                widget.CurrentLayout(),
                widget.GroupBox(),
                widget.Prompt(),
                widget.WindowName(),
                extrawidgets.UPowerWidget(),
                widget.Clock(format='%Y-%m-%d %a %I:%M %p'),
                widget.QuickExit(),
            ],
            24,
        ),
    ),
]
```

### Customising

The widget allows the battery icon to be resized and to display colours for different states.

The widget can be customised with the following arguments:

<table>
    <tr>
            <td>font</td>
            <td>Default font</td>
    </tr>
    <tr>
            <td>fontsize</td>
            <td>Font size</td>
    </tr>
    <tr>
            <td>font_colour</td>
            <td>Font colour for information text</td>
    </tr>
    <tr>
            <td>battery_height</td>
            <td>Height of battery icon</td>
    </tr>
    <tr>
            <td>battery_width</td>
            <td>Size of battery icon</td>
    </tr>
    <tr>
            <td>battery_name</td>
            <td>Battery name. None = all batteries</td>
    </tr>
    <tr>
            <td>border_charge_colour</td>
            <td>Border colour when charging.</td>
    </tr>
    <tr>
            <td>border_colour</td>
            <td>Border colour when discharging.</td>
    </tr>
    <tr>
            <td>border_critical_colour</td>
            <td>Border colour when battery low.</td>
    </tr>
    <tr>
            <td>fill_normal</td>
            <td>Fill when normal</td>
    </tr>
    <tr>
            <td>fill_low</td>
            <td>Fill colour when battery low</td>
    </tr>
    <tr>
            <td>fill_critical</td>
            <td>Fill when critically low</td>
    </tr>
    <tr>
            <td>margin</td>
            <td>Margin on sides of widget</td>
    </tr>
    <tr>
            <td>spacing</td>
            <td>Space between batteries</td>
    </tr>
    <tr>
            <td>percentage_low</td>
            <td>Low level threshold.</td>
    </tr>
    <tr>
            <td>percentage_critical</td>
            <td>Critical level threshold.</td>
    </tr>
    <tr>
            <td>text_charging</td>
            <td>Text to display when charging.</td>
    </tr>
    <tr>
            <td>text_discharging</td>
            <td>Text to display when on battery.</td>
    </tr>
    <tr>
            <td>text_displaytime</td>
            <td>Time for text to remain before hiding</td>
    </tr>
</table>


