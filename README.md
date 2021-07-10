# elParaguayo's Qtile Extras

This is a separate repo where I share things that I made for qtile that (probably) won't ever end up in the main repo.

This things were really just made for use by me so your mileage may vary.

Currently available extras:
* Widgets
  * [ALSA Volume Control](#alsa-volume-control-and-widget)
  * [Brightness Control](#brightness-control)
  * [Live Football Scores](#live-football-scores)
  * [Script Exit](#script-exit)
  * [Unit Status](#unit-status)
  * [UPower battery indicator](#upower-widget)


## ALSA Volume Control and Widget

This module provides basic volume controls and a simple icon widget showing volume level for Qtile.

### About

The module is very simple and, so far, just allows controls for volume up, down and mute.

Volume control is handled by running the appropriate amixer command. The widget is updated instantly when volume is changed via this code, but will also update on an interval (i.e. it will reflect changes to volume made by other programs).

The widget displays volume level via an icon, bar or both. The icon is permanently visible while the bar only displays when the volume is changed and will hide after a user-defined period.

### Demo

Here is a screenshot from my HTPC showing the widget in the bar. The icon theme currently shown is called "Paper".

_"Icon" mode:_</br>
![Screenshot](images/volumecontrol-icon.gif?raw=true)

_"Bar" mode:_</br>
![Screenshot](images/volumecontrol-bar.gif?raw=true)

_"Both" mode:_</br>
![Screenshot](images/volumecontrol-both.gif?raw=true)


### Configuration

Add the code to your config (`~/.config/qtile/config.py`):

```python
from qtile_extras import widget as extrawidgets

keys = [
...
Key([], "XF86AudioRaiseVolume", lazy.widget["alsawidget"].volume_up()),
Key([], "XF86AudioLowerVolume", lazy.widget["alsawidget"].volume_down()),
Key([], "XF86AudioMute", lazy.widget["alsawidget"].toggle_mute()),
...
]

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.CurrentLayout(),
                widget.GroupBox(),
                widget.Prompt(),
                widget.WindowName(),
                extrawidgets.ALSAWidget(),
                widget.Clock(format='%Y-%m-%d %a %I:%M %p'),
                widget.QuickExit(),
            ],
            24,
        ),
    ),
]
```

### Customising

The volume control assumes the "Master" device is being updated and that volume is changed by 5%. 

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
            <td>mode</td>
            <td>Display mode: 'icon', 'bar', 'both'.</td>
    </tr>
    <tr>
            <td>hide_interval</td>
            <td>Timeout before bar is hidden after update</td>
    </tr>
    <tr>
            <td>text_format</td>
            <td>String format</td>
    </tr>
    <tr>
            <td>bar_width</td>
            <td>Width of display bar</td>
    </tr>
    <tr>
            <td>bar_colour_normal</td>
            <td>Colour of bar in normal range</td>
    </tr>
    <tr>
            <td>bar_colour_high</td>
            <td>Colour of bar if high range</td>
    </tr>
    <tr>
            <td>bar_colour_loud</td>
            <td>Colour of bar in loud range</td>
    </tr>
    <tr>
            <td>bar_colour_mute</td>
            <td>Colour of bar if muted</td>
    </tr>
    <tr>
            <td>limit_normal</td>
            <td>Max percentage for normal range</td>
    </tr>
    <tr>
            <td>limit_high</td>
            <td>Max percentage for high range</td>
    </tr>
    <tr>
            <td>limit_loud</td>
            <td>Max percentage for loud range</td>
    </tr>
    <tr>
            <td>update_interval</td>
            <td>Interval to update widget (e.g. if changes made in other apps).</td>
    </tr>
    <tr>
            <td>theme_path</td>
            <td>Path to theme icons.</td>
    </tr>
    <tr>
            <td>device</td>
            <td>Name of ALSA output (default: "Master").</td>
    </tr>
    <tr>
            <td>tstep</td>
            <td>Amount to change volume by.</td>
    </tr>
</table>

Note: it may be preferable to set the "theme_path" via the "widget_defaults" variable in your config.py so that themes are applied consistently across widgets.


## Brightness Control

This module provides basic screen brightness controls and a simple widget showing the brightness level for Qtile.

### About

Brightness control is handled by writing to the appropriate /sys/class/backlight device. The widget is updated instantly when the brightness is changed via this code and will autohide after a user-defined timeout.

### Demo

Here is an animated gif showing the widget in the bar.

![Demo](images/brightnesscontrol-demo.gif?raw=true)

### Write access to backlight device

This script will not work unless the user has write access to the relevant backlight device.

This can be achieved via a udev rule which modifies the group and write permissions. The rule should be saved /etc/udev/rules.d

An example rule is as follows:
```
# Udev rule to change group and write permissions for screen backlight
ACTION=="add", SUBSYSTEM=="backlight", KERNEL=="intel_backlight", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness"
ACTION=="add", SUBSYSTEM=="backlight", KERNEL=="intel_backlight", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
```

You should then ensure that your user is a member of the "video" group.

### Configuration

Add the code to your config (`~/.config/qtile/config.py`):

```python
from qtile_extras import widget as extrawidgets

keys = [
...
Key([], "XF86MonBrightnessUp", lazy.widget["brightnesscontrol"].brightness_up()),
Key([], "XF86MonBrightnessDown", lazy.widget["brightnesscontrol"].brightness_down()),
...
]

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.CurrentLayout(),
                widget.GroupBox(),
                widget.Prompt(),
                widget.WindowName(),
                extrawidgets.BrightnessControl(),
                widget.Clock(format='%Y-%m-%d %a %I:%M %p'),
                widget.QuickExit(),
            ],
            24,
        ),
    ),
]
```

## Customising

The widget allows for significant customisation and can accept the following parameters:

<table>
    <tr>
        <td>device</td>
        <td>path to the backlight device. Defaults to /sys/class/backlight/intel_backlight</td>
    </tr>
    <tr>
        <td>brightness_path</td>
        <td>the name of the 'file' containing the brightness value NB the user needs to have write access to this path</td>
    </tr>
    <tr>
        <td>max_brightness_path</td>
        <td>the 'file' that stores the maximum brightness value for the device. This can be overriden by the user - see below.</td>
    </tr>
    <tr>
        <td>min_brightness</td>
        <td>define a lower limit for screen brightness to prevent screen going completely dark.</td>
    </tr>
    <tr>
        <td>max_brightness</td>
        <td>define a maximum limit e.g. if you don't want to go to full brightness. Use None to use system defined value.</td>
    </tr>
    <tr>
        <td>step</td>
        <td>Amount to change brightness (accepts int or percentage as string)</td>
    </tr>
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
            <td>Colour of text.</td>
    </tr>
    <tr>
            <td>text_format</td>
            <td>Text to display.</td>
    </tr>
    <tr>
            <td>bar_colour</td>
            <td>Colour of bar displaying brightness level.</td>
    </tr>
    <tr>
            <td>error_colour</td>
            <td>Colour of bar when displaying an error</td>
    </tr>
    <tr>
            <td>timeout_interval</td>
            <td>Time before widget is hidden.</td>
    </tr>
    <tr>
            <td>widget_width</td>
            <td>Width of bar when widget displayed</td>
    </tr>
    <tr>
            <td>enable_power_saving</td>
            <td>Automatically set brightness depending on status (mains or battery)</td>
    </tr>
    <tr>
            <td>brightness_on_mains</td>
            <td>Brightness level on mains power (accepts integer value or percentage as string)</td>
    </tr>
    <tr>
            <td>brightness_on_battery</td>
            <td>Brightness level on battery power (accepts integer value or percentage as string)</td>
    </tr>
</table>


## Live Football Scores

This module provides a simple widget showing the live football (soccer for any of you in the US) scores.

### About

The module uses a module I wrote a number of years ago that parses data from the BBC Sport website.

The underlying module needs work so it will probably only work if you pick a "big" team.

You can select more than one team and league. Scores can be scrolled by using the mousewheel over the widget.

### Demo

Here is a screenshot showing the widget in the bar.

![Screenshot](images/livefootballscores.gif?raw=true)</br>
(The different screens show: live score, elapsed time, home and away goalscorers and competition name. In addition, the amount of text shown can be customised by using python's string formatting techniques e.g. the default line "{H:.3} {h}-{a} {A:.3}" shows the first 3 letters of team names rather than the full name as shown above.)

### Indicators

Goals and red cards are indicated by a coloured bar next to the relevant team name. The match status is indicated by a coloured bar underneath the match summary. All colours are customisable.

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
                extrawidgets.LiveFootballScores(team="St Mirren"),     # As shown in screenshot
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
                <td>Text colour</td>
        </tr>
        <tr>
                <td>team</td>
                <td>Team whose scores you want to display</td>
        </tr>
        <tr>
                <td>teams</td>
                <td>List of other teams whose scores you want to display</td>
        </tr>
        <tr>
                <td>leagues</td>
                <td>Leagues whose scores you want to display</td>
        </tr>
        <tr>
                <td>status_text</td>
                <td>Default widget match text</td>
        </tr>
        <tr>
                <td>info_text</td>
                <td>Add extra text lines which can be displayed by clicking on widget.
        Available fields are:</br>
         {H}: Home Team name</br>
         {A}: Away Team name</br>
         {h}: Home score</br>
         {a}: Away score</br>
         {C}: Competition</br>
         {v}: Venue</br>
         {T}: Display time (kick-off, elapsed time, HT, FT)</br>
         {S}: Status (as above but no elapsed time)</br>
         {G}: Home goalscorers</br>
         {g}: Away goalscorers</br>
         {R}: Home red cards</br>
         {r}: Away red cards</td></blockquote>
        </tr>
        <tr>
                <td>refresh_interval</td>
                <td>Time to update data</td>
        </tr>
        <tr>
                <td>info_timeout</td>
                <td>Time before reverting to default text</td>
        </tr>
        <tr>
                <td>startup_delay</td>
                <td>TDelay before first data request (enables quicker loading)</td>
        </tr>
        <tr>
                <td>goal_indicator</td>
                <td>Colour of line to show team that scores</td>
        </tr>
        <tr>
                <td>red_card_indicator</td>
                <td>Colour of line to show team has had a player sent off.</td>
        </tr>
        <tr>
                <td>always_show_red</td>
                <td>Continue to show red card indicator</td>
        </tr>
        <tr>
                <td>underline_status</td>
                <td>Bar at bottom of widget to indicate status.</td>
        </tr>
        <tr>
                <td>status_fixture</td>
                <td>Colour when match has not started</td>
        </tr>
        <tr>
                <td>status_live</td>
                <td>Colour when match is live</td>
        </tr>
        <tr>
                <td>status_halftime</td>
                <td>Colour when half time</td>
        </tr>
        <tr>
                <td>status_fulltime</td>
                <td>Colour when match has ended</td>
        </tr>
</table>



## Script Exit

A modified version of the QuickExit widget that take an additional parameter (`exit_script`) which is the path of a script to be run before exiting Qtile.

```python
from qtile_extras import widget as extrawidgets

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.CurrentLayout(),
                widget.GroupBox(),
                widget.Prompt(),
                widget.WindowName(),
                widget.Clock(format='%Y-%m-%d %a %I:%M %p'),
                extrawidgets.ScriptExit(
                    exit_script='/path/to/exit/script'
                ),
            ],
            24,
        ),
    ),
]
```

## Unit Status

UnitStatus is a basic widget for Qtile which shows the current status of systemd units.

It may not be particular useful for you and was primarily written as an exercise to familiarise myself with writing Qtile widgets and interacting with d-bus.

### About

The widget is incredibly basic. It subscribes to the systemd d-bus interface, finds the relevant service and displays an icon based on the current status. The widget listens for announced changes to the service and updates the icon accordingly.

### Demo

Here is a screenshot showing multiple instances of the widget. Green icons are active services and the white is inactive.

![Screenshot](images/widget-unitstatus-screenshot.png?raw=true)

### Configuration

Add the widget to your config (`~/.config/qtile/config.py`):

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
                extrawidgets.UnitStatus(label="Avahi",unitname="avahi-daemon.service"),
                extrawidgets.UnitStatus(), # NetworkManager.service is default
                widget.Clock(format='%Y-%m-%d %a %I:%M %p'),
                widget.QuickExit(),
            ],
            24,
        ),
    ),
]
```

### Customising

The widget can be customised with the following arguments:

<table>
    <tr>
            <td>bus_name</td>
            <td>Which bus to use. Accepts 'system' or 'session'</td>
    </tr>
    <tr>
            <td>font</td>
            <td>Default font</td>
    </tr>
    <tr>
            <td>fontsize</td>
            <td>Font size</td>
    </tr>
    <tr>
            <td>unitname</td>
            <td>Name of systemd unit.</td>
    </tr>
    <tr>
            <td>label</td>
            <td>Short text to display next to indicator.</td>
    </tr>
    <tr>
            <td>colour_active</td>
            <td>Colour for active indicator</td>
    </tr>
    <tr>
            <td>colour_inactive</td>
            <td>Colour for active indicator</td>
    </tr>
    <tr>
            <td>colour_failed</td>
            <td>Colour for active indicator</td>
    </tr>
    <tr>
            <td>colour_dead</td>
            <td>Colour for dead indicator</td>
    </tr>
    <tr>
            <td>indicator_size</td>
            <td>Size of indicator (None = up to margin)</td>
    </tr>
    <tr>
            <td>state_map</td>
            <td>Map of indicator colours (state: (border, fill))<br />
            {"active": ("colour_active", "colour_active"),
             "inactive": ("colour_inactive", "colour_inactive"),
             "deactivating": ("colour_inactive", "colour_active"),
             "activating": ("colour_active", "colour_inactive"),
             "failed": ("colour_failed", "colour_failed"),
             "not-found": ("colour_inactive", "colour_failed"),
             "dead": ("colour_dead", "colour_dead"),
           }</td>
    </tr>
</table>


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


