# Copyright (c) 2023, elParaguayo. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from libqtile.hook import Hook, Registry

hooks: list[Hook] = []

# Live Football Scores
footballscores_hooks = [
    Hook(
        "lfs_goal_scored",
        """
        LiveFootballScores widget.

        Fired when the score in a match changes.

        Hooked function should receive one argument which is the
        ``FootballMatch`` object for the relevant match.

        Note: as the widget polls all matches at the same time, you
        may find that the hook is fired multiple times in quick succession.
        Handling multiple hooks is left to the user to manage.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.lfs_goal_scored
          def goal(match):
              if "Arsenal" in (match.home_team, match.away_team):
                qtile.spawn("ffplay goal.wav")

        """,
    ),
    Hook(
        "lfs_status_change",
        """
        LiveFootballScores widget.

        Fired when the match status changes (i.e. kick-off, half time etc.).

        Hooked function should receive one argument which is the
        ``FootballMatch`` object for the relevant match.

        Note: as the widget polls all matches at the same time, you
        may find that the hook is fired multiple times in quick succession.
        Handling multiple hooks is left to the user to manage.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.lfs_status_change
          def status(match):
              if match.is_finished and "Arsenal" in (match.home_team, match.away_team):
                  qtile.spawn("ffplay whistle.wav")

        """,
    ),
    Hook(
        "lfs_red_card",
        """
        LiveFootballScores widget.

        Fired when a red card is issued in a match.

        Hooked function should receive one argument which is the
        ``FootballMatch`` object for the relevant match.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.lfs_red_card
          def red_card(match):
              if "Arsenal" in (match.home_team, match.away_team):
                  qtile.spawn("ffplay off.wav")

        """,
    ),
]

hooks.extend(footballscores_hooks)

# TVHeadend
tvh_hooks = [
    Hook(
        "tvh_recording_started",
        """
        TVHeadend widget.

        Fired when a recording starts.

        Hooked function should receive one argument which is the
        name of the program being recorded.

        .. code:: python

          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.tvh_recording_started
          def start_recording(prog):
              send_notification("Recording Started", prog)

        """,
    ),
    Hook(
        "tvh_recording_ended",
        """
        TVHeadend widget.

        Fired when a recording ends.

        Hooked function should receive one argument which is the
        name of the program that was recorded.

        .. code:: python

          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.tvh_recording_ended
          def stop_recording(prog):
              send_notification("Recording Ended", prog)

        """,
    ),
]

hooks.extend(tvh_hooks)

# Githubnotifications
githubnotifications_hooks = [
    Hook(
        "ghn_new_notification",
        """
        GithubNotifications widget.

        Fired when there is a new notification.

        Note: the hook will only be fired whenever the widget
        polls.

        .. code:: python

          from libqtile import qtile
          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.ghn_new_notification
          def ghn_notification():
              qtile.spawn("ffplay ding.wav")

        """,
    )
]

hooks.extend(githubnotifications_hooks)

# Upower
upower_hooks = [
    Hook(
        "up_power_connected",
        """
        UPowerWidget.

        Fired when a power supply is connected.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.up_power_connected
          def plugged_in():
              qtile.spawn("ffplay power_on.wav")

        """,
    ),
    Hook(
        "up_power_disconnected",
        """
        UPowerWidget.

        Fired when a power supply is disconnected.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.up_power_disconnected
          def unplugged():
              qtile.spawn("ffplay power_off.wav")

        """,
    ),
    Hook(
        "up_battery_full",
        """
        UPowerWidget.

        Fired when a battery is fully charged.

        .. code:: python

          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.up_battery_full
          def battery_full(battery_name):
              send_notification(battery_name, "Battery is fully charged.")

        """,
    ),
    Hook(
        "up_battery_low",
        """
        UPowerWidget.

        Fired when a battery reaches low threshold.

        .. code:: python

          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.up_battery_low
          def battery_low(battery_name):
              send_notification(battery_name, "Battery is running low.")

        """,
    ),
    Hook(
        "up_battery_critical",
        """
        UPowerWidget.

        Fired when a battery is critically low.

        .. code:: python

          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.up_battery_critical
          def battery_critical(battery_name):
              send_notification(battery_name, "Battery is critically low. Plug in power supply.")

        """,
    ),
]

hooks.extend(upower_hooks)

# Syncthing hooks
syncthing_hooks = [
    Hook(
        "st_sync_started",
        """
        Syncthing widget.

        Fired when a sync starts.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.st_sync_started
          def sync_start():
              qtile.spawn("ffplay start.wav")

        """,
    ),
    Hook(
        "st_sync_stopped",
        """
        Syncthing widget.

        Fired when a sync stops.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.st_sync_stopped
          def sync_stop():
              qtile.spawn("ffplay complete.wav")

        """,
    ),
]

hooks.extend(syncthing_hooks)

# MPRIS2 widget
mpris_hooks = [
    Hook(
        "mpris_new_track",
        """
        Mpris2 widget.

        Fired when a track changes. Receives a dict of the new metadata.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.mpris_new_track
          def new_track(metadata):
              if metadata["xesam:title"] == "Never Gonna Give You Up":
                  qtile.spawn("max_volume.sh")

        """,
    ),
    Hook(
        "mpris_status_change",
        """
        Mpris2 widget.

        Fired when the playback status changes. Receives a string containing the new status.

        .. code:: python

          from libqtile import qtile

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.mpris_status_change
          def new_track(status):
              if status == "Stopped":
                  qtile.spawn("mute.sh")
              else:
                  qtile.spawn("unmute.sh")

        """,
    ),
]

hooks.extend(mpris_hooks)

# Volume hooks
volume_hooks = [
    Hook(
        "volume_change",
        """
        Fired when the volume value changes.

        Receives an integer volume percentage (0-100) and boolean muted status.

        .. code:: python

          from libqtile import qtile
          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.volume_change
          def vol_change(volume, muted):
              send_notification("Volume change", f"Volume is now {volume}%")

        """,
    ),
    Hook(
        "volume_mute_change",
        """
        Fired when the volume mute status changes.

        Receives an integer volume percentage (0-100) and boolean muted status.

        The signature is the same as ``volume_change`` to allow the same function to be
        used for both hooks.

        .. code:: python

          from libqtile import qtile
          from libqtile.utils import send_notification

          import qtile_extras.hook

          @qtile_extras.hook.subscribe.volume_mute_change
          def mute_change(volume, muted):
              if muted:
                send_notification("Volume change", "Volume is now muted.")

        """,
    ),
]

hooks.extend(volume_hooks)

# Build the registry and expose helpful entrypoints
qte = Registry("qtile-extras", hooks)

subscribe = qte.subscribe
unsubscribe = qte.unsubscribe
fire = qte.fire
