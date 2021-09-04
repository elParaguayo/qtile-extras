from libqtile import bar, pangocffi
from libqtile.log_utils import logger
from libqtile.popup import Popup
from libqtile.widget import base

from qtile_extras.resources.footballscores import (FootballMatch,
                                                   FSConnectionError, League)


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
        return any([self.homegoal,
                    self.awaygoal,
                    self.statuschange,
                    self.homered,
                    self.awayred])

    def reset(self):
        self._reset()


class LiveFootballScores(base._Widget, base.MarginMixin):
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
    """

    orientations = base.ORIENTATION_HORIZONTAL
    _experimental = True

    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("font_colour", "ffffff", "Text colour"),
        ("team", "Liverpool", "Team whose scores you want to display"),
        ("teams", [], "List of other teams you want to display"),
        ("leagues", [], "List of leagues you want to display"),
        ("status_text", "{H:.3} {h}-{a} {A:.3}", "Default widget match text"),
        ("info_text",
            ["{T:^12}",
             "{H:.3}: {G:10}",
             "{A:.3}: {g:10}",
             "{C}"],
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
             """),
        ("popup_text", "{H:>20.20} {h}-{a} {A:<20.20} {T:<5}",
            "Format to use for popup window."),
        ("refresh_interval", 60, "Time to update data"),
        ("info_timeout", 5, "Time before reverting to default text"),
        ("startup_delay", 30, "Time before sending first web request"),
        ("goal_indicator", "009999",
            "Colour of line to show team that scores"),
        ("red_card_indicator", "bb0000",
            "Colour of line to show team has had a player sent off."),
        ("always_show_red", True, "Continue to show red card indicator"),
        ("underline_status", True,
            "Bar at bottom of widget to indicate status."),
        ("status_fixture", "000000", "Colour when match has not started"),
        ("status_live", "008800", "Colour when match is live"),
        ("status_halftime", "aaaa00", "Colour when half time"),
        ("status_fulltime", "666666", "Colour when match has ended"),
        (
            "popup_font",
            "monospace",
            "Font to use for displaying upcoming recordings. A monospace font "
            "is recommended"
        ),
        (
            "popup_opacity",
            0.8,
            "Opacity for popup window."
        ),
        (
            "popup_padding",
            10,
            "Padding for popup window."
        ),
        (
            "popup_display_timeout",
            10,
            "Seconds to show recordings."
        ),
    ]

    _screenshots = [
        (
            "livefootballscores.gif",
            "The different screens show: live score, elapsed time, "
            "home and away goalscorers and competition name. In "
            "addition, the amount of text shown can be customised by "
            "using python's string formatting techniques e.g. the "
            "default line '{H:.3} {h}-{a} {A:.3}' shows the first 3 "
            "letters of team names rather than the full name as "
            "shown above."
        ),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(LiveFootballScores.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        self.flags = {}
        self.reset_flags()

        self.sources = ([], [], [])
        self.matches = []
        self.match_index = 0

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
                "Button3": self.toggle_info,
                "Button4": self.scroll_up,
                "Button5": self.scroll_down
            }
        )

    def reset_flags(self):
        for flag in self.flags:
            self.flags[flag].reset()

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

    def cmd_reboot(self):
        return self.reboot()

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.matches = []
        self.timeout_add(self.startup_delay, self.setup)

    def setup(self):
        self.qtile.run_in_executor(self._setup)

    def _setup(self):
        kwargs = {"detailed": True,
                  "on_goal": self.match_event,
                  "on_red": self.match_event,
                  "on_status_change": self.match_event,
                  "on_new_match": self.match_event}

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
        self.refresh_timer = self.timeout_add(self.refresh_interval,
                                              self.refresh)

    def refresh(self):
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

        elif event.is_red:
            flags.homered = event.home
            flags.awayred = not event.home

        elif event.is_status_change:
            flags.statuschange = True

        if flags.changes:
            self.queue_update()

    def queue_update(self):
        if self.queue_timer:
            self.queue_timer.cancel()

        self.queue_timer = self.timeout_add(1, self.bar.draw)

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

        width, _ = self.drawer.max_layout_size(
            [text],
            self.font,
            self.fontsize
        )

        return width + 2 * self.margin

    def draw(self):
        # Remove background
        self.drawer.clear(self.background or self.bar.background)

        m = self.get_match()

        if m:
            screen = self.screens[self.screen_index]
            text = m.format_text(screen)
        else:
            text = ""

        # Create a text box
        layout = self.drawer.textlayout(text,
                                        self.font_colour,
                                        self.font,
                                        self.fontsize,
                                        None,
                                        wrap=False)

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

                if flags.homered or (self.always_show_red and
                                     m.home_red_cards):
                    self.draw_red(True)

                if flags.awayred or (self.always_show_red and
                                     m.away_red_cards):
                    self.draw_red(False)

                if self.underline_status:
                    self.draw_underline(m)

        # # Redraw the bar
        self.drawer.draw(
            offsetx=self.offset,
            offsety=self.offsety,
            width=self.length
        )

    def draw_goal(self, home):
        offset = 0 if home else (self.width - 2)

        self.drawer.set_source_rgb(self.goal_indicator)

        # Draw the bar
        self.drawer.fillrect(offset,
                             0,
                             2,
                             self.height,
                             2)

    def draw_red(self, home):
        offset = 0 if home else (self.width - 2)

        self.drawer.set_source_rgb(self.red_card_indicator)

        # Draw the bar
        self.drawer.fillrect(offset,
                             self.height/2,
                             2,
                             self.height/2,
                             2)

    def draw_underline(self, m):
        offset = 2
        width = self.width - 2

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
            self.drawer.fillrect(
                offset,
                self.height - 2,
                width,
                2,
                2
            )

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

        self.default_timer = self.timeout_add(self.info_timeout,
                                              self.show_default)

    def show_default(self):
        # Show first screen
        self.screen_index = 0
        self.bar.draw()

    def cmd_info(self):
        str_team = self.team
        str_teams = ",".join(self.teams)
        str_leagues = ",".join(self.leagues)
        obj_team = ",".join([str(team) for team in self.sources[0]])

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

        return {"name": self.name,
                "sources": {
                    "team": str_team,
                    "teams": str_teams,
                    "leagues": str_leagues
                },
                "objects": {
                    "team": obj_team,
                    "teams": obj_teams,
                    "leagues": obj_leagues
                },
                "matches": matches
                }

    def cmd_refresh(self):
        return self.refresh()

    def _format_matches(self):
        lines = []

        for team in [m for m in self.sources[0] if m]:
            lines.append(team.competition)
            lines.append(team.format_text(self.popup_text))
            lines.append("")

        if self.sources[1]:
            lines.append("Selected Teams:")
            for team in [m for m in self.sources[1] if m]:
                lines.append(team.format_text(self.popup_text))
            lines.append("")

        for league in self.sources[2]:
            if league:
                lines.append("{}:".format(league.league_name))
                for team in league:
                    lines.append(team.format_text(self.popup_text))
                lines.append("")

        # Last line is always blank so remove it
        _ = lines.pop()

        return lines

    @property
    def bar_on_top(self):
        return self.bar.screen.top == self.bar

    def kill_popup(self):
        self.popup.kill()
        self.popup = None

    def toggle_info(self):
        if self.popup and not self.popup.win.hidden:
            try:
                self.hide_timer.cancel()
            except AttributeError:
                pass
            self.kill_popup()

        else:
            self.show_matches()

    def cmd_popup(self):
        self.toggle_info()

    def show_matches(self):
        lines = []

        if not self.matches:
            lines.append("No matches today.")

        else:
            lines.extend(self._format_matches())

        self.popup = Popup(self.qtile,
                           width=self.bar.screen.width,
                           height=self.bar.screen.height,
                           font=self.popup_font,
                           horizontal_padding=self.popup_padding,
                           vertical_padding=self.popup_padding,
                           opacity=self.popup_opacity)

        text = pangocffi.markup_escape_text("\n".join(lines))

        self.popup.text = text

        self.popup.height = (self.popup.layout.height +
                             (2 * self.popup.vertical_padding))
        self.popup.width = (self.popup.layout.width +
                            (2 * self.popup.horizontal_padding))

        self.popup.x = min(self.offsetx, self.bar.width - self.popup.width)

        if self.bar_on_top:
            self.popup.y = self.bar.height
        else:
            self.popup.y = (self.bar.screen.height - self.popup.height -
                            self.bar.height)

        self.popup.place()
        self.popup.draw_text()
        self.popup.unhide()
        self.popup.draw()

        self.hide_timer = self.timeout_add(self.popup_display_timeout,
                                           self.kill_popup)
