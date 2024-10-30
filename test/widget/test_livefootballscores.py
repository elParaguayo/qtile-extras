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
import logging
from datetime import datetime

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
import requests.exceptions

import qtile_extras.widget.livefootballscores
from qtile_extras.resources.footballscores import footballmatch, league
from qtile_extras.resources.footballscores.matchevent import MatchEvent
from qtile_extras.resources.footballscores.utils import UTC
from test.helpers import Retry
from test.widget.resources import lfs_data


@Retry(ignore_exceptions=(AssertionError,))
def matches_loaded(manager):
    _, output = manager.c.widget["livefootballscores"].eval("self.matches")
    assert output != "[]"


@Retry(ignore_exceptions=(AssertionError,))
def restore_default_screen(manager):
    _, output = manager.c.widget["livefootballscores"].eval("self.screen_index")
    assert int(output) == 0


@Retry(ignore_exceptions=(AssertionError,))
def check_timer(manager):
    _, output = manager.c.widget["livefootballscores"].eval("self.refresh_timer")
    # Ugly but it works!
    assert output.startswith("<TimerHandle")


class MatchRequest:
    status_code = 200
    error = False

    def __init__(self, url, params=dict()):
        self.url = url
        self.params = params
        self.urn = params.get("urn", "")
        if self.error:
            raise requests.exceptions.ConnectionError

    def json(self):
        if "chelsea" in self.urn or "west-ham-united" in self.urn:
            return lfs_data.CHELSEA
        elif "liverpool" in self.urn:
            return lfs_data.LIVERPOOL
        # Ugly hack to get the premier league data when no tournament provided!
        elif "premier-league" in self.urn or "tournament-collection:collated" in self.urn:
            return lfs_data.PREMIER_LEAGUE
        else:
            return lfs_data.NO_MATCHES


@pytest.fixture(scope="function")
def lfs_match(monkeypatch):
    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.footballmatch.requests.get", MatchRequest
    )
    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.footballmatch.requests.head", MatchRequest
    )
    yield footballmatch.FootballMatch


@pytest.fixture(scope="function")
def lfs_league(monkeypatch):
    monkeypatch.setattr("qtile_extras.resources.footballscores.league.requests.get", MatchRequest)
    yield league.League


@pytest.fixture(scope="function")
def lfswidget(monkeypatch, lfs_match):
    monkeypatch.setattr("qtile_extras.widget.livefootballscores.FootballMatch", lfs_match)
    monkeypatch.setattr(
        "qtile_extras.widget.livefootballscores.LiveFootballScores._queue_time", 0
    )
    yield qtile_extras.widget.livefootballscores


@pytest.fixture(scope="function")
def lfs_manager(lfswidget):
    class FootieConfig(libqtile.confreader.Config):
        auto_fullscreen = True
        keys = []
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = [libqtile.layout.Max()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar(
                    [
                        lfswidget.LiveFootballScores(
                            team="Chelsea",
                            teams=["Liverpool", "Real Madrid"],
                            leagues=["premier-league", "FIFA World Cup"],
                            startup_delay=0,
                            info_timeout=0.3,
                        )
                    ],
                    50,
                ),
            )
        ]

    yield FootieConfig


def test_scores_display_and_navigation(lfs_manager, manager_nospawn):
    """Test basic display functions for the widget."""
    manager_nospawn.start(lfs_manager)

    # Wait until matches have loaded
    matches_loaded(manager_nospawn)

    # There should be 10 matches (1x "team", 1x "teams" and
    # 4 in "leagues")
    _, output = manager_nospawn.c.widget["livefootballscores"].eval("len(self.matches)")
    assert int(output) == 6

    # Default display is "team"
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Wes 1-5 Che"

    # Right-clicking loops through different displays
    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 1)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "FT"

    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 1)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Wes: Lucas Paquetá (6')"

    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 1)
    assert manager_nospawn.c.widget["livefootballscores"].get() == (
        "Che: João Pedro (15'), Pedro Neto (23'), E. Fernández (34'), M. Caicedo (54'), T. Chalobah (58')"
    )

    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 1)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Premier League"

    # Waiting will revert to score display
    restore_default_screen(manager_nospawn)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Wes 1-5 Che"

    # Test mouse scrolling to select match - this is "teams"
    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 4)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Liv 1-0 Ars"

    # Test mouse scrolling to select match - this is "leagues"
    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 4)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Bri 2-1 Man"

    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 5)
    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 5)
    assert manager_nospawn.c.widget["livefootballscores"].get() == "Wes 1-5 Che"


def test_widget_reboot(lfs_manager, manager_nospawn):
    """Check reboot command resets matches."""
    manager_nospawn.start(lfs_manager)

    # Wait until matches have loaded
    matches_loaded(manager_nospawn)
    # Rebooting should reset matches
    manager_nospawn.c.widget["livefootballscores"].reboot()
    matches_loaded(manager_nospawn)


def test_widget_info(lfs_manager, manager_nospawn):
    """Check info() output."""
    manager_nospawn.start(lfs_manager)

    # Wait until matches have loaded
    matches_loaded(manager_nospawn)

    # info() gives us a lot of data!
    info = manager_nospawn.c.widget["livefootballscores"].info()
    assert info == {
        "name": "livefootballscores",
        "sources": {
            "team": "Chelsea",
            "teams": "Liverpool, Real Madrid",
            "leagues": "premier-league, FIFA World Cup",
        },
        "objects": {
            "team": "West Ham United 1-5 Chelsea (FT)",
            "teams": {
                "Liverpool": "Liverpool 1-0 Arsenal (FT)",
                "Real Madrid": "Real Madrid are not playing today.",
            },
            "leagues": {
                "premier-league": {
                    0: "Brighton & Hove Albion 2-1 Manchester City (FT)",
                    1: "Nottingham Forest 0-3 West Ham United (FT)",
                    2: "Liverpool 1-0 Arsenal (FT)",
                    3: "Aston Villa 0-3 Crystal Palace (FT)",
                },
                "FIFA World Cup": {},
            },
        },
        "matches": {
            0: "West Ham United 1-5 Chelsea (FT)",
            1: "Liverpool 1-0 Arsenal (FT)",
            2: "Brighton & Hove Albion 2-1 Manchester City (FT)",
            3: "Nottingham Forest 0-3 West Ham United (FT)",
            4: "Liverpool 1-0 Arsenal (FT)",
            5: "Aston Villa 0-3 Crystal Palace (FT)",
        },
    }


def test_widget_popup(lfs_manager, manager_nospawn):
    """Check popup display."""
    manager_nospawn.start(lfs_manager)

    # Wait until matches have loaded
    matches_loaded(manager_nospawn)

    assert len(manager_nospawn.c.internal_windows()) == 1

    manager_nospawn.c.bar["top"].fake_button_press(0, 0, 3)
    assert len(manager_nospawn.c.internal_windows()) == 2

    # Each menu item is a tuple of:
    # - boolean: whether menu item is text (True) or a separator (False)
    # - string: text contents
    # - boolean: whether item is enable or not
    items = (
        (True, "Premier League", False),
        (True, "West Ham United 1-5 Chelsea (FT)", True),
        (False, "", False),
        (True, "Selected Teams:", False),
        (True, "Liverpool 1-0 Arsenal (FT)", True),
        (False, "", False),
        (True, "Premier League:", False),
        (True, "Brighton & Hove Albi 2-1 Manchester City (FT)", True),
        (True, "Nottingham Forest 0-3 West Ham United (FT)", True),
        (True, "Liverpool 1-0 Arsenal (FT)", True),
        (True, "Aston Villa 0-3 Crystal Palace (FT)", True),
    )

    for i, (is_text, match, enabled) in enumerate(items):
        if is_text:
            _, text = manager_nospawn.c.widget["livefootballscores"].eval(
                f"self.menu.controls[{i}].text"
            )
            assert text == match
            _, is_enabled = manager_nospawn.c.widget["livefootballscores"].eval(
                f"self.menu.controls[{i}].enabled"
            )
            assert str(enabled) == is_enabled
        else:
            _, class_type = manager_nospawn.c.widget["livefootballscores"].eval(
                f"type(self.menu.controls[{i}])"
            )
            assert "PopupMenuSeparator" in class_type

    manager_nospawn.c.widget["livefootballscores"].popup()
    _, popup = manager_nospawn.c.widget["livefootballscores"].eval("self.popup")
    assert popup == "None"


def test_widget_refresh(lfs_manager, manager_nospawn, caplog):
    """Check refresh command resets timer."""
    manager_nospawn.start(lfs_manager)

    # Wait until matches have loaded
    matches_loaded(manager_nospawn)

    manager_nospawn.c.widget["livefootballscores"].eval("self.set_refresh_timer()")
    manager_nospawn.c.widget["livefootballscores"].eval("self.refresh_timer.cancel()")
    manager_nospawn.c.widget["livefootballscores"].eval("self.refresh_timer = None")
    with caplog.at_level(logging.INFO):
        manager_nospawn.c.widget["livefootballscores"].refresh()
        check_timer(manager_nospawn)
        assert caplog.record_tuples == []


def test_footballmatch_module_equality(lfs_match):
    """Football matches should be equal if they're the same game."""
    che = lfs_match("Chelsea")
    whu = lfs_match("West Ham United")

    che.update()
    whu.update()

    assert che == whu


def test_footballmatch_module_inequality(lfs_match, monkeypatch):
    """Inequality scenarios"""
    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.FootballMatch._find_team_page", lambda _: False
    )

    # Scenario 1: inequality if there's no match ID and myteam is not the same
    home = lfs_match("first")
    away = lfs_match("second")
    assert home != away

    # Scenario 2: inequality if not compared with a FootballMatch instance
    assert home != "String"


def test_footballmatch_module_matchdate(lfs_match):
    """Football matches can receive a match date"""

    # Valid match date
    che = lfs_match("Chelsea", matchdate="2021-11-06")
    assert che._matchdate == "2021-11-06"

    # Invalid match date
    with pytest.raises(ValueError):
        _ = lfs_match("Burnley", matchdate="2021-11-32")


def test_footballmatch_module_scanleagues(lfs_match, monkeypatch):
    """Find team in match page."""

    # Pretend we can't find a team page to force scanning
    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.FootballMatch._find_team_page", lambda _: False
    )
    sth = lfs_match("Crystal Palace")

    assert sth.home_team == "Aston Villa"
    assert sth.away_team == "Crystal Palace"


def test_footballmatch_module_no_matchdata(lfs_match, monkeypatch):
    """Check output when no match."""

    def no_match(*args, **kwargs):
        return lfs_data.NO_MATCHES

    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.FootballMatch._get_scores_fixtures", no_match
    )
    che = lfs_match("Chelsea")
    assert str(che) == "Chelsea are not playing today."


def test_footballmatch_module_format_match(lfs_match):
    """Test string formatting."""
    che = lfs_match("Chelsea")
    assert che.format_match("%H %A") == "West Ham United Chelsea"


def test_footballmatch_module_kickoff_time(lfs_match, monkeypatch):
    """Test time formatting"""

    # Mock datetime to show time being 13:45
    class MockDatetime(datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            return cls(2021, 11, 6, 13, 45, 0, tzinfo=UTC())

    # Force match to show as a fixture
    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.FootballMatch.is_fixture", lambda _: True
    )
    monkeypatch.setattr(
        "qtile_extras.resources.footballscores.footballmatch.datetime", MockDatetime
    )
    che = lfs_match("Chelsea")

    # Time to kick-off is 19:00 - 13:45 == 1 hr and 15 mins
    assert che.format_time_to_kick_off("{h}:{m}") == "5:15"


def test_footballmatch_module_last_events(lfs_match):
    """Retrieve last events."""
    che = lfs_match("Chelsea")
    lg = che.last_goal
    assert lg.is_goal
    assert lg.name == "T. Chalobah"

    hg = che.last_home_goal
    assert hg.is_goal
    assert hg.name == "Lucas Paquetá"

    ag = che.last_away_goal
    assert ag == lg

    lr = che.last_red_card
    assert not lr


def test_league_module_update(lfs_league):
    """Checks that update adds new matches."""
    prem = lfs_league("premier-league")
    assert prem

    count = len(prem)

    # Remove all matches
    prem.matches = []

    # Check that update restores all matches
    prem.update()
    assert prem

    # Remove one match
    prem.matches.pop(0)

    # Check that update just adds missing matches
    prem.update()
    assert len(prem) == count


def test_league_module_tournament_name(lfs_league):
    """Check handling of tournament name."""
    prem = lfs_league("premier-league")

    # If there's a match, take the name from that match
    assert prem.league_name == "Premier League"

    # If there are no matches, take value from init
    prem.matches = []
    assert prem.league_name == "premier-league"


def test_matchevent_module(lfs_match):
    """Basic tests of MatchEvent module."""
    che = lfs_match("Chelsea")

    home_goal = MatchEvent(MatchEvent.TYPE_GOAL, che, home=True)
    assert home_goal.is_goal
    assert not home_goal.is_red
    assert not home_goal.is_status_change
    assert not home_goal.is_live
    assert not home_goal.is_new_match
    assert not home_goal.is_fixture
    assert home_goal.scorer.name == "Lucas Paquetá"

    away_goal = MatchEvent(MatchEvent.TYPE_GOAL, che, home=False)
    assert away_goal.is_goal
    assert not away_goal.is_red
    assert not away_goal.is_status_change
    assert not away_goal.is_live
    assert not away_goal.is_new_match
    assert not away_goal.is_fixture
    assert away_goal.scorer.name == "T. Chalobah"

    home_red = MatchEvent(MatchEvent.TYPE_RED_CARD, che, home=True)
    assert not home_red.is_goal
    assert home_red.is_red
    assert home_red.red_card is None

    away_red = MatchEvent(MatchEvent.TYPE_RED_CARD, che, home=False)
    assert not away_red.is_goal
    assert away_red.is_red
    assert away_red.red_card is None

    status = MatchEvent(MatchEvent.TYPE_STATUS, che)
    assert status.is_status_change
    assert status.is_finished


def test_livefootballscores_deprecated_font_colour(caplog):
    widget = qtile_extras.widget.LiveFootballScores(font_colour="ffffff")

    assert caplog.record_tuples[0] == (
        "libqtile",
        logging.WARNING,
        "The use of `font_colour` is deprecated. "
        "Please update your config to use `foreground` instead.",
    )

    assert widget.foreground == "ffffff"
