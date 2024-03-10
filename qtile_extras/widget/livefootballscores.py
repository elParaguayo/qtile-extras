# Copyright (c) 2015-2021 elParaguayo
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
from typing import TYPE_CHECKING

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base

from qtile_extras import hook
from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupText
from qtile_extras.resources.footballscores import FootballMatch, FSConnectionError, League
from qtile_extras.widget.mixins import ExtendedPopupMixin, MenuMixin

if TYPE_CHECKING:
    from typing import Any  # noqa: F401


DETAILED_LAYOUT = PopupRelativeLayout(
    width=700,
    height=200,
    controls=[
        PopupText(fontsize=15, pos_x=0.1, pos_y=0.1, width=0.3, height=0.1, name="competition"),
        PopupText(
            fontsize=20,
            v_align="middle",
            h_align="right",
            pos_x=0.05,
            pos_y=0.3,
            width=0.35,
            height=0.2,
            name="home_team",
        ),
        PopupText(
            fontsize=25,
            v_align="middle",
            h_align="center",
            pos_x=0.45,
            pos_y=0.3,
            width=0.1,
            height=0.2,
            name="score",
        ),
        PopupText(
            fontsize=20,
            v_align="middle",
            h_align="left",
            pos_x=0.6,
            pos_y=0.3,
            width=0.35,
            height=0.2,
            name="away_team",
        ),
        PopupText(
            fontsize=15,
            h_align="right",
            v_align="top",
            pos_x=0.05,
            pos_y=0.6,
            width=0.35,
            height=0.2,
            name="home_scorers",
        ),
        PopupText(
            fontsize=15,
            h_align="center",
            v_align="top",
            pos_x=0.45,
            pos_y=0.6,
            width=0.1,
            height=0.2,
            name="display_time",
        ),
        PopupText(
            fontsize=15,
            h_align="left",
            v_align="top",
            pos_x=0.6,
            pos_y=0.6,
            width=0.35,
            height=0.2,
            name="away_scorers",
        ),
    ],
)


# Massively overkill to use a class here...
class MatchFlags(object):
    def __init__(self):
        self._reset()

    def _reset(self):
        self.homegoal = False
        self.awaygoal = False
        self.statuschange = False
        self.homered = False
        self.awayred = False

    @property
    def changes(self):
        return any([self.homegoal, self.awaygoal, self.statuschange, self.homered, self.awayred])

    def reset(self):
        self._reset()


class LiveFootballScores(base._Widget, base.MarginMixin, ExtendedPopupMixin, MenuMixin):
    """
    The module uses a module I wrote a number of years ago that parses
    data from the BBC Sport website.

    The underlying module needs work so it will probably only work if
    you pick a "big" team.

    You can select more than one team and league. Scores can be scrolled
    by using the mousewheel over the widget.

    Goals and red cards are indicated by a coloured bar next to the
    relevant team name. The match status is indicated by a coloured bar
    underneath the match summary. All colours are customisable.

    Right-clicking the widget will bring up a list of all matches that meet your
    selected criteria. Clicking on any of those matches will open a popup showing
    more detail.

    The popup can be accessed directly by the ``show_detail()`` command.
    When this is used, the selected match is the one currently visible in
    the widget.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    _experimental = True

    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("foreground", "ffffff", "Text colour"),
        ("team", "Liverpool", "Team whose scores you want to display"),
        ("teams", [], "List of other teams you want to display"),
        ("leagues", [], "List of leagues you want to display"),
        ("status_text", "{H:.3} {h}-{a} {A:.3}", "Default widget match text"),
        (
            "info_text",
            ["{T:^12}", "{H:.3}: {G:10}", "{A:.3}: {g:10}", "{C}"],
            """
            Add extra text lines which can be displayed by clicking on widget.
            Available fields are:
             {H}: Home Team name
             {A}: Away Team name
             {h}: Home score
             {a}: Away score
             {C}: Competition
             {v}: Venue
             {T}: Display time (kick-off, elapsed time, HT, FT)
             {S}: Status (as above but no elapsed time)
             {G}: Home goalscorers
             {g}: Away goalscorers
             {R}: Home red cards
             {r}: Away red cards
             """,
        ),
        ("popup_text", "{H:.20} {h}-{a} {A:.20} ({T:.5})", "Format to use for popup window."),
        ("refresh_interval", 60, "Time to update data"),
        ("info_timeout", 5, "Time before reverting to default text"),
        ("startup_delay", 30, "Time before sending first web request"),
        ("goal_indicator", "009999", "Colour of line to show team that scores"),
        (
            "red_card_indicator",
            "bb0000",
            "Colour of line to show team has had a player sent off.",
        ),
        ("always_show_red", True, "Continue to show red card indicator"),
        ("underline_status", True, "Bar at bottom of widget to indicate status."),
        ("status_fixture", "000000", "Colour when match has not started"),
        ("status_live", "008800", "Colour when match is live"),
        ("status_halftime", "aaaa00", "Colour when half time"),
        ("status_fulltime", "666666", "Colour when match has ended"),
        (
            "popup_font",
            "monospace",
            "Font to use for displaying upcoming recordings. A monospace font " "is recommended",
        ),
        ("popup_display_timeout", 10, "Seconds to show recordings."),
        ("menu_width", 300, "Width of menu showing all matches"),
        ("popup_layout", DETAILED_LAYOUT, "Layout to use for extended match information"),
        (
            "popup_show_args",
            {"centered": True, "hide_on_timeout": 5},
            "Arguments to set behaviour of extended popup",
        ),
    ]  # type: list[tuple[str, Any, str]]

    _screenshots = [
        (
            "livefootballscores.gif",
            "The different screens show: live score, elapsed time, "
            "home and away goalscorers and competition name. In "
            "addition, the amount of text shown can be customised by "
            "using python's string formatting techniques e.g. the "
            "default line ``{H:.3} {h}-{a} {A:.3}`` shows the first 3 "
            "letters of team names rather than the full name as "
            "shown above.",
        ),
    ]

    _dependencies = ["requests"]
    _queue_time = 1
    _hooks = [h.name for h in hook.footballscores_hooks]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        ExtendedPopupMixin.__init__(self, **config)
        self.add_defaults(MenuMixin.defaults)
        self.add_defaults(ExtendedPopupMixin.defaults)
        self.add_defaults(LiveFootballScores.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        MenuMixin.__init__(self, **config)

        if "font_colour" in config:
            self.foreground = config["font_colour"]
            logger.warning(
                "The use of `font_colour` is deprecated. "
                "Please update your config to use `foreground` instead."
            )

        if "popup_opacity" in config:
            self.opacity = config["popup_opacity"]
            logger.warning(
                "The use of `popup_opacity` is deprecated. "
                "Please update your config to use `opacity` instead."
            )

        self.flags = {}
        self.reset_flags()

        self.sources = ([], [], [])
        self.matches = []
        self.match_index = 0
        self._selected_match = None

        # Define our screens
        self.screens = [self.status_text] + self.info_text
        self.screen_index = 0

        # Initial variables to hide text
        self.show_text = False
        self.default_timer = None
        self.refresh_timer = None
        self.queue_timer = None

        self.popup = None

        self.add_callbacks(
            {
                "Button1": self.loop_match_info,
                "Button3": self.show_matches,
                "Button4": self.scroll_up,
                "Button5": self.scroll_down,
            }
        )

    def reset_flags(self):
        for flag in self.flags:
            self.flags[flag].reset()

    @expose_command()
    def reboot(self):
        """
        Sometimes the widget won't update (and I don't know why).
        This method should reset everything and start the widget again.

        Can be bound to a key e.g.:
           lazy.widget["livefootballscores"].reboot
        """

        timers = [self.queue_timer, self.default_timer, self.refresh_timer]
        _ = [timer.cancel() for timer in timers if timer]

        self.flags = {}
        self.matches = []
        self.sources = ([], [], [])

        self.timeout_add(1, self.setup)

        return True

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.matches = []
        self.timeout_add(self.startup_delay, self.setup)

    def setup(self):
        self.qtile.run_in_executor(self._setup)

    def _setup(self):
        kwargs = {
            "detailed": True,
            "on_goal": self.match_event,
            "on_red": self.match_event,
            "on_status_change": self.match_event,
            "on_new_match": self.match_event,
        }

        try:
            # Create foorball match object
            if not self.sources[0]:
                myteam = FootballMatch(self.team, **kwargs)
                self.sources[0].append(myteam)

            if not self.sources[1] and self.teams:
                self.sources[1].clear()
                for team in self.teams:
                    self.sources[1].append(FootballMatch(team, **kwargs))

            if not self.sources[2] and self.leagues:
                self.sources[2].clear()
                for league in self.leagues:
                    self.sources[2].append(League(league, **kwargs))

            self.get_matches()
            self.set_refresh_timer()
            self.queue_update()

        except FSConnectionError:
            logger.info("Unable to get football scores data.")

            # Check if we managed to create all teams and leagues objects
            if len(self.sources[1]) != len(self.teams):
                self.sources[1].clear()

            if len(self.sources[2]) != len(self.leagues):
                self.sources[2].clear()

            # Can't connect, so let's try again later
            self.timeout_add(5, self.setup)

    def get_matches(self):
        self.matches = []

        if self.sources[0]:
            self.matches.extend([x for x in self.sources[0] if x])

        if self.sources[1]:
            self.matches.extend([x for x in self.sources[1] if x])

        if self.sources[2]:
            for league in self.sources[2]:
                if league:
                    # League object has iterator methods
                    # so can be treated as a list
                    self.matches.extend(league)

        self.set_flags()

    def set_flags(self):
        for m in self.matches:
            if m.home_team not in self.flags:
                self.flags[m.home_team] = MatchFlags()

        current = [x.home_team for x in self.matches]

        for old in [x for x in self.flags if x not in current]:
            del self.flags[old]

    def set_refresh_timer(self):
        self.refresh_timer = self.timeout_add(self.refresh_interval, self.refresh)

    @expose_command()
    def refresh(self):
        """Force a poll of match data."""
        self.qtile.run_in_executor(self._refresh)

    def _refresh(self):
        success = False
        self.reset_flags()
        try:
            if self.sources[0]:
                _ = [x.update() for x in self.sources[0]]

            if self.sources[1]:
                _ = [x.update() for x in self.sources[1]]

            if self.sources[2]:
                _ = [x.update() for x in self.sources[2]]

            self.get_matches()

            self.queue_update()

            success = True

        except FSConnectionError:
            logger.info("Unable to refresh football scores data.")
            if self.queue_timer:
                self.queue_timer.cancel()

        self.set_refresh_timer()

        return success

    def match_event(self, event):
        self.set_flags()

        team = event.match.home_team

        try:
            flags = self.flags[team]
        except KeyError:
            # This should only happen when a new match
            # for watched teams appears
            # Events are fired on first time,
            # before they can be added to the flags
            # It should be safe to ignore this
            # as the flags will be updated separately
            self.flags[team] = MatchFlags()
            flags = self.flags[team]

        if event.is_goal:
            flags.homegoal = event.home
            flags.awaygoal = not event.home
            hook.fire("lfs_goal_scored", event.match)

        elif event.is_red:
            flags.homered = event.home
            flags.awayred = not event.home
            hook.fire("lfs_red_card", event.match)

        elif event.is_status_change:
            flags.statuschange = True
            hook.fire("lfs_status_change", event.match)

        if flags.changes:
            self.queue_update()

    def queue_update(self):
        if self.queue_timer:
            self.queue_timer.cancel()

        self.queue_timer = self.timeout_add(self._queue_time, self.bar.draw)

    def get_match(self):
        if self.match_index >= len(self.matches):
            self.match_index = 0

        try:
            return self.matches[self.match_index]
        except IndexError:
            return None

    def calculate_length(self):
        m = self.get_match()

        if m:
            screen = self.screens[self.screen_index]
            text = m.format_text(screen)
        else:
            text = ""

        width, _ = self.drawer.max_layout_size([text], self.font, self.fontsize)

        return width + 2 * self.margin if width else 0

    def draw(self):
        # Remove background
        self.drawer.clear(self.background or self.bar.background)

        m = self.get_match()

        if m:
            screen = self.screens[self.screen_index]
            self.text = m.format_text(screen)
        else:
            self.text = ""

        # Create a text box
        layout = self.drawer.textlayout(
            self.text, self.foreground, self.font, self.fontsize, None, wrap=False
        )

        # We want to centre this vertically
        y_offset = (self.bar.height - layout.height) / 2

        # Draw it
        layout.draw(self.margin_x, y_offset)

        if m:
            flags = self.flags[m.home_team]

            if self.screen_index == 0:
                if flags.homegoal:
                    self.draw_goal(True)

                if flags.awaygoal:
                    self.draw_goal(False)

                if flags.homered or (self.always_show_red and m.home_red_cards):
                    self.draw_red(True)

                if flags.awayred or (self.always_show_red and m.away_red_cards):
                    self.draw_red(False)

                if self.underline_status:
                    self.draw_underline(m)

        # # Redraw the bar
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

    def draw_goal(self, home):
        offset = 0 if home else (self.calculate_length() - 2)

        self.drawer.set_source_rgb(self.goal_indicator)

        # Draw the bar
        self.drawer.fillrect(offset, 0, 2, self.height, 2)

    def draw_red(self, home):
        offset = 0 if home else (self.calculate_length() - 2)

        self.drawer.set_source_rgb(self.red_card_indicator)

        # Draw the bar
        self.drawer.fillrect(offset, self.height / 2, 2, self.height / 2, 2)

    def draw_underline(self, m):
        offset = 2
        width = self.calculate_length() - 2

        if m.is_fixture:
            fill = self.status_fixture
        elif m.is_live:
            fill = self.status_live
        elif m.is_half_time:
            fill = self.status_halftime
        elif m.is_finished:
            fill = self.status_fulltime
        else:
            fill = None

        if fill is not None:
            self.drawer.set_source_rgb(fill)

            # Draw the bar
            self.drawer.fillrect(offset, self.height - 2, width, 2, 2)

    def loop_match_info(self):
        self.set_default_timer()
        self.screen_index = (self.screen_index + 1) % len(self.screens)
        self.bar.draw()

    def scroll_up(self):
        self.change_match(1)

    def scroll_down(self):
        self.change_match(-1)

    def change_match(self, step):
        self.screen_index = 0
        if self.matches:
            self.match_index = (self.match_index + step) % len(self.matches)
            self.bar.draw()

    def set_default_timer(self):
        if self.default_timer:
            self.default_timer.cancel()

        self.default_timer = self.timeout_add(self.info_timeout, self.show_default)

    def show_default(self):
        # Show first screen
        self.screen_index = 0
        self.bar.draw()

    @expose_command()
    def info(self):
        """Show information about all matches"""
        str_team = self.team
        str_teams = ", ".join(self.teams)
        str_leagues = ", ".join(self.leagues)
        obj_team = ", ".join([str(team) for team in self.sources[0]])

        obj_teams = {}
        for team in self.sources[1]:
            obj_teams[team.myteam] = str(team)

        obj_leagues = {}
        for league in self.sources[2]:
            obj_leagues[league.league] = {}
            for i, m in enumerate(league):
                obj_leagues[league.league][i] = str(m)

        matches = {}
        for i, m in enumerate(self.matches):
            matches[i] = str(m)

        return {
            "name": self.name,
            "sources": {"team": str_team, "teams": str_teams, "leagues": str_leagues},
            "objects": {"team": obj_team, "teams": obj_teams, "leagues": obj_leagues},
            "matches": matches,
        }

    def kill_popup(self):
        self.popup.kill()
        self.popup = None

    def toggle_info(self):
        if self.menu and not self.menu._killed:
            self.menu.kill()
        else:
            self.show_matches()

    @expose_command()
    def popup(self):
        """Display window listing all matches"""
        self.toggle_info()

    @expose_command()
    def get(self):
        """Get displayed text. Removes padding."""
        return self.text.strip()

    @expose_command()
    def show_detail(self):
        """Displays popup showing detailed info about match."""
        self.update_or_show_popup()

    def _update_popup(self):
        selected = self._selected_match
        current = self.get_match()

        team = selected if selected is not None else current

        self.extended_popup.update_controls(
            competition=team.competition,
            home_team=team.home_team,
            away_team=team.away_team,
            score=team.format_text("{h} - {a}"),
            home_scorers=team.home_scorer_text.replace("), ", ")\n"),
            away_scorers=team.away_scorer_text.replace("), ", ")\n"),
            display_time=team.display_time,
        )

        self._selected_match = None

    def select_match(self, match):
        self._selected_match = match
        self.update_or_show_popup()

    def _get_match_list(self):
        lines = []

        pmi = self.create_menu_item
        pms = self.create_menu_separator

        def _callback(team):
            return {"mouse_callbacks": {"Button1": lambda team=team: self.select_match(team)}}

        for team in [m for m in self.sources[0] if m]:
            lines.extend(
                [
                    pmi(text=team.competition, enabled=False),
                    pmi(text=team.format_text(self.popup_text), **_callback(team)),
                ]
            )

        if self.sources[1]:
            if lines and any(m for m in self.sources[1]):
                lines.append(pms())

            lines.append(pmi(text="Selected Teams:", enabled=False))

            for team in [m for m in self.sources[1] if m]:
                lines.append(pmi(text=team.format_text(self.popup_text), **_callback(team)))

        for league in self.sources[2]:
            if lines and league:
                lines.append(pms())
            if league:
                lines.append(pmi(text="{}:".format(league.league_name), enabled=False))
                for team in league:
                    lines.append(pmi(text=team.format_text(self.popup_text), **_callback(team)))

        if not lines:
            lines.append(pmi(text="No matches today", enabled=False))

        return lines

    @expose_command
    def show_matches(
        self,
        x=None,
        y=None,
        centered=False,
        warp_pointer=False,
        relative_to=1,
        relative_to_bar=False,
        hide_on_timeout=None,
    ):
        """Show menu with followed matchs."""
        self.display_menu(
            menu_items=self._get_match_list(),
            x=x,
            y=y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )
