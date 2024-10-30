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
from __future__ import annotations

from datetime import datetime, timezone
from itertools import groupby
from typing import TYPE_CHECKING

import requests

from qtile_extras.resources.footballscores.exceptions import FSConnectionError
from qtile_extras.resources.footballscores.matchdict import MatchDict
from qtile_extras.resources.footballscores.matchdict import MatchDictKeys as MDKey
from qtile_extras.resources.footballscores.matchevent import MatchEvent
from qtile_extras.resources.footballscores.playeraction import PlayerAction
from qtile_extras.resources.footballscores.utils import UTC, get_time_tuple

if TYPE_CHECKING:
    from typing import Any


# We need a UTC timezone to do some datetime manipulations
TZ_UTZ = UTC()

# API_BASE = "http://push.api.bbci.co.uk"
API_BASE = "https://web-cdn.api.bbci.co.uk/wc-poll-data/container/sport-data-scores-fixtures"

URN_PREFIX = "urn:bbc:sportsdata:football:"
URN_ALL = f"{URN_PREFIX}tournament-collection:collated"

# https://web-cdn.api.bbci.co.uk/wc-poll-data/container/sport-data-scores-fixtures?selectedEndDate=2024-09-28&selectedStartDate=2024-09-28&todayDate=2024-09-28&urn=urn%3Abbc%3Asportsdata%3Afootball%3Atournament-collection%3Acollated&useSdApi=false

# team
# https://web-cdn.api.bbci.co.uk/wc-poll-data/container/sport-data-scores-fixtures?selectedEndDate=2024-09-28&selectedStartDate=2024-09-28&todayDate=2024-09-28&urn=urn%3Abbc%3Asportsdata%3Afootball%3Ateam%3Achelsea&useSdApi=false

# tournament
# https://web-cdn.api.bbci.co.uk/wc-poll-data/container/sport-data-scores-fixtures?selectedEndDate=2024-09-21&selectedStartDate=2024-09-21&todayDate=2024-09-22&urn=urn%3Abbc%3Asportsdata%3Afootball%3Atournament%3Apremier-league&useSdApi=false


class FootballMatch:
    """Class for getting details of individual football matches.
    Data is pulled from BBC live scores page.
    """

    match_format = {
        "%H": "home_team",
        "%A": "away_team",
        "%h": "home_score",
        "%a": "away_score",
        "%T": "display_time",
        "%S": "status",
        "%R": "home_red_cards",
        "%r": "away_red_cards",
        "%G": "home_scorer_text",
        "%g": "away_scorer_text",
        "%C": "competition",
    }

    ACTION_GOAL = "goal"
    ACTION_RED_CARD = "card"

    STATUS_LIVE = "LIVE"
    STATUS_PENALTIES = "PENALLTIES"
    STATUS_POSTPONED = "POSTPONED"
    STATUS_HALF_TIME = "HALFTIME"
    STATUS_FULL_TIME = "FULLTIME"
    STATUS_FIXTURE = "FIXTURE"
    STATUS_ET_FIRST_HALF = "EXTRATIMEFIRSTHALF"
    STATUS_ET_HALF_TIME = "EXTRATIMEHALFTIME"

    def __init__(
        self,
        team,
        detailed=True,
        data=None,
        on_goal=None,
        on_red=None,
        on_status_change=None,
        on_new_match=None,
        matchdate=None,
        events_on_first_run=False,
        update=True,
    ):
        """Creates an instance of the Match object.
        Must be created by passing the name of one team.

        data - User can also send data to the class e.g. if multiple instances
        of class are being run thereby saving http requests. Otherwise class
        can handle request on its own.

        detailed - Do we want additional data (e.g. goal scorers, bookings)?
        """
        super().__init__()
        self.detailed = detailed
        self.myteam = team
        self.match = MatchDict()
        self._matchdate = self._check_match_date(matchdate)

        self._on_red = on_red
        self._on_goal = on_goal
        self._on_status_change = on_status_change
        self._on_new_match = on_new_match

        self._clear_flags()

        self.previous_status = None

        if data is None:
            self.hasTeamPage = self._find_team_page()

            if not self.hasTeamPage:
                data = self._scan_leagues()

            else:
                self.update(first_run=events_on_first_run)

        if data and update:
            self.update(data=data, first_run=events_on_first_run)

    def __nonzero__(self):
        return bool(self.match)

    def __bool__(self):
        return self.__nonzero__()

    def __repr__(self):
        return f"<FootballMatch('{self.myteam}')>"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if all([self.match.id, other.match.id]):
                try:
                    return self.match.id == other.match.id
                except AttributeError:
                    pass
            return self.myteam == other.myteam
        else:
            return False

    # Semi-hidden methods, only meant to be called by other class methods

    def _no_match(default: Any):  # noqa: N805
        """
        Decorator to provide default values for properties when there is no
        match found.

        e.g.:
            @property
            @_no_match(str())
            def home_team(self):
                ...
        """

        def wrapper(func):
            def wrapped(self):
                if self.match:
                    return func(self)

                else:
                    return default

            return wrapped

        return wrapper

    def _override_none(value: Any):  # noqa: N805
        """
        Decorator to provide default values for properties when there is no
        current value.

        For example, this decorator can be used to convert a None value for a
        match score (empty before the match starts) to 0.

        e.g.:
            @property
            @_no_match(int())
            @_override_none(0)
            def home_score(self):
                ...
        """

        def wrapper(func):
            def wrapped(self):
                if func(self) is None:
                    return value

                else:
                    return func(self)

            return wrapped

        return wrapper

    def _request(self, **data):
        try:
            r = requests.get(API_BASE, params=data)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise FSConnectionError

        if r.status_code == 200:
            return r.json()
        else:
            return dict()

    def check_page(self, page):
        try:
            rq = requests.head(page)
            return rq.status_code == 200
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return False

    def _check_match_date(self, matchdate):
        if matchdate is None:
            return None

        try:
            datetime.strptime(matchdate, "%Y-%m-%d")
            return matchdate

        except (ValueError, TypeError):
            raise ValueError("Invalid match date. " "Match date format must by YYYY-MM-DD.")

    def _can_update(self):
        return self.hasTeamPage

    def _scan_leagues(self):
        payload = self._get_scores_fixtures(source=URN_ALL)

        for group in payload["eventGroups"]:
            for subgroup in group["secondaryGroups"]:
                for game in subgroup["events"]:
                    if self.check_team_in_match(game):
                        return game

        return None

    def check_team_in_match(self, m):
        home = [m["home"][x].lower() for x in ["fullName", "shortName"] if m["home"][x]]

        away = [m["away"][x].lower() for x in ["fullName", "shortName"] if m["away"][x]]

        return self.myteam.lower() in (home + away)

    def _find_team_page(self):
        team = "-".join(self.myteam.lower().split(" "))
        teampage = "https://www.bbc.co.uk/sport/football/teams/" + team
        validteam = self.check_page(teampage)
        if validteam:
            self.myteampage = f"team/{team}"
            return True
        else:
            return False

    def _get_scores_fixtures(self, start_date=None, end_date=None, source=None, detailed=None):
        if start_date is None:
            if self._matchdate:
                start_date = self._matchdate
            else:
                start_date = datetime.now().strftime("%Y-%m-%d")

        if end_date is None:
            if self._matchdate:
                end_date = self._matchdate
            else:
                end_date = datetime.now().strftime("%Y-%m-%d")

        if source is not None:
            urn = source
        elif self.hasTeamPage:
            urn = f"{URN_PREFIX}{self.myteampage.replace("/", ":")}"
        else:
            urn = URN_ALL

        data = dict(
            selectedStartDate=start_date,
            selectedEndDate=end_date,
            todayDate=datetime.now().strftime("%Y-%m-%d"),
            urn=urn,
        )

        return self._request(**data)

    def _find_match(self, payload):
        match = payload["eventGroups"]

        if match:
            return match[0]["secondaryGroups"][0]["events"][0]  # noqa: E501
        else:
            return None

    def _set_callbacks(self):
        self.match.add_callback("home", self._check_home_team_event)
        self.match.add_callback("away", self._check_away_team_event)
        self.match.add_callback(MDKey.PROGRESS, self._check_status)

    def _get_events(self, event, event_type):
        events = []

        player_actions = event.get("actions", list())

        for acts in player_actions:
            if acts["actionType"] == event_type:
                events += PlayerAction.get_all(acts)

        return sorted(events)

    def _last_event(self, event_type, just_home=False, just_away=False):
        events = []

        if just_home and just_away:
            just_home = just_away = False

        if not just_away:
            events += self._get_events(self.match.home, event_type)

        if not just_home:
            events += self._get_events(self.match.away, event_type)

        events = sorted(events)

        if events:
            return events[-1]
        else:
            return None

    def _last_reds(self, just_home=False, just_away=False):
        reds = []
        red = self._last_event(self.ACTION_RED_CARD, just_home=just_home, just_away=just_away)

        if red:
            reds.append(red)

        if reds:
            return sorted(reds)[-1]
        else:
            return None

    def _get_reds(self, event):
        reds = []
        reds += self._get_events(event, self.ACTION_RED_CARD)
        return sorted(reds)

    def _get_goals(self, event):
        return self._get_events(event, self.ACTION_GOAL)

    def _check_goal(self, old, new):
        if not (
            (isinstance(new.score, str) and new.score.isnumeric()) or isinstance(new.score, int)
        ):
            return False
        return (old.score != new.score) and (int(new.score) > 0)

    def _check_red(self, old, new):
        old_reds = self._get_reds(old)
        new_reds = self._get_reds(new)

        return old_reds != new_reds

    def _check_home_team_event(self, event):
        self._check_team_event(event, home=True)

    def _check_away_team_event(self, event):
        self._check_team_event(event, home=False)

    def _check_team_event(self, event, home=True):
        if home:
            old = self._old.home
        else:
            old = self._old.away

        new = MatchDict(event)

        goal = self._check_goal(old, new)
        red = self._check_red(old, new)

        if goal:
            if home:
                self._homegoal = True
            else:
                self._awaygoal = True

        if red:
            if home:
                self._homered = True
            else:
                self._awayred = True

    def _check_status(self, status):
        self._statuschange = self.status != self.previous_status
        self.previous_status = self.status

    def _clear_flags(self):
        self._homegoal = False
        self._awaygoal = False
        self._homered = False
        self._awayred = False
        self._statuschange = False
        self._matchfound = False

    def _fire(self, func, payload):
        try:
            func(payload)
        except TypeError:
            pass

    def _fire_events(self):
        if self._homegoal:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_GOAL, self, True)
            self._fire(func, payload)

        if self._awaygoal:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_GOAL, self, False)
            self._fire(func, payload)

        if self._homered:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_RED_CARD, self, True)
            self._fire(func, payload)

        if self._awayred:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_RED_CARD, self, False)
            self._fire(func, payload)

        if self._statuschange:
            func = self.on_status_change
            payload = MatchEvent(MatchEvent.TYPE_STATUS, self)
            self._fire(func, payload)

        if self._matchfound:
            func = self.on_new_match
            payload = MatchEvent(MatchEvent.TYPE_NEW_MATCH, self)
            self._fire(func, payload)

    def _grouped_events(self, events):
        # Sort events by name
        events = sorted(events, key=lambda x: x.name)
        # Group events by name (list of lists)
        events = [list(y) for x, y in groupby(events, key=lambda x: x.name)]
        # Sort the player groups so the earliest goal is first
        events = sorted(events, key=lambda x: x[0]._time_tuple)
        # Sort the goals in time order (shouldn't be necessary...)
        events = [sorted(x, key=lambda x: x._time_tuple) for x in events]

        return events

    def _format_events(self, events):
        events = self._grouped_events(events)

        raw = []
        out = ""

        for event in events:
            name = event[0].name
            times = []

            if event[0].is_goal and event[0].is_own_goal:
                name = f"{name} (OG)"

            for item in event:
                dt = item.display_time

                if item.is_goal and item.is_penalty:
                    dt = f"{dt} pen"

                times.append(dt)

            raw.append((name, times))

        for i, (player, events) in enumerate(raw):
            out += player
            ev = " ("
            ev += ", ".join(events)
            ev += ")"

            out += ev

            if i < len(raw) - 1:
                out += ", "

        return out

    def format_text(self, text):
        values = {k[1]: getattr(self, v) for k, v in self.match_format.items()}
        return text.format(**values)

    def format_match(self, fmt):
        for key in self.match_format:
            try:
                fmt = fmt.replace(key, getattr(self, self.match_format[key]))
            except TypeError:
                fmt = fmt.replace(key, str(getattr(self, self.match_format[key])))

        return fmt

    def format_time_to_kick_off(self, fmt):
        ko = self.time_to_kick_off

        if ko is None:
            return ""

        d = {"d": ko.days}
        d["h"], rem = divmod(ko.seconds, 3600)
        d["m"], d["s"] = divmod(rem, 60)
        d["s"] = int(d["s"])

        return fmt.format(**d)

    def update(self, data=None, first_run=False):
        if data is None and not self._can_update():
            data = self._scan_leagues()

        elif data is None:
            rawdata = self._get_scores_fixtures()
            if rawdata:
                match = self._find_match(rawdata)
            else:
                match = None

        if data:
            match = data

        if match:
            self._clear_flags()
            if not self.match:
                self.match = MatchDict(match, add_callbacks=True)
                self._set_callbacks()
                self.previous_status = self.status
                self._matchfound = True

            else:
                self.match.update(match)

            if not first_run:
                self._fire_events()
            self._old = self.match

            return True

        # Need this to clear the match if no data (e.g. next day)
        elif match is None and self.match:
            self._clear_flags()
            self.match = MatchDict()
            return True

        return False

    #
    # # Neater functions to return data:
    #

    @property
    def on_goal(self):
        if self._on_goal:
            return self._on_goal

    @on_goal.setter
    def on_goal(self, func):
        if callable(func):
            self._on_goal = func

    @property
    def on_red(self):
        if self._on_red:
            return self._on_red

    @on_red.setter
    def on_red(self, func):
        if callable(func):
            self._on_red = func

    @property
    def on_status_change(self):
        if self._on_status_change:
            return self._on_status_change

    @on_status_change.setter
    def on_status_change(self, func):
        if callable(func):
            self._on_status_change = func

    @property
    def on_new_match(self):
        if self._on_new_match:
            return self._on_new_match

    @on_new_match.setter
    def on_new_match(self, func):
        if callable(func):
            self._on_new_match = func

    @property
    @_no_match("")
    def home_team(self):
        """Returns string of the home team's name"""
        return self.match.home.fullName

    @property
    @_no_match("")
    def away_team(self):
        """Returns string of the away team's name"""
        return self.match.away.fullName

    @property
    @_no_match(0)
    @_override_none(0)
    def home_score(self):
        """Returns the number of goals scored by the home team"""
        return self.match.home.score

    @property
    @_no_match(0)
    @_override_none(0)
    def away_score(self):
        """Returns the number of goals scored by the away team"""
        return self.match.away.score

    @property
    @_no_match(0)
    @_override_none(0)
    def home_score_penalties(self):
        """Returns the number of goals scored by the home team"""
        if not self.is_penalty_shootout:
            return None
        return self.match.home.runningScores.penaltyShootout

    @property
    @_no_match(0)
    @_override_none(0)
    def away_score_penalties(self):
        """Returns the number of goals scored by the away team"""
        if not self.is_penalty_shootout:
            return None
        return self.match.away.runningScores.penaltyShootout

    @property
    @_no_match("")
    def competition(self):
        """Returns the name of the competition to which the match belongs

        e.g. "Premier League", "FA Cup" etc

        """
        return self.match.tournament.name

    @property
    @_no_match("")
    def status(self):
        """Returns the status of the match

        e.g. "L", "HT", "FT"

        """
        # return self.match.eventProgress.period
        status = getattr(self.match, "status", None)
        if status == "PreEvent":
            return self.STATUS_FIXTURE
        elif status == "MidEvent":
            if self.long_status == "Half time":
                return self.STATUS_HALF_TIME
            elif self.long_status == "Penalty shootout":
                return self.STATUS_PENALTIES
            else:
                return self.STATUS_LIVE
        elif status == "PostEvent":
            return self.STATUS_FULL_TIME
        elif status == "Postponed":
            return self.STATUS_POSTPONED
        return status or ""

    @property
    @_no_match("")
    def long_status(self):
        return self.match.statusComment.accessible

    @property
    @_no_match("")
    def display_time(self):
        me = self.elapsed_time
        et = self.added_time

        miat = f"+{et}" if et else ""

        if self.status == self.STATUS_POSTPONED:
            return "P"

        elif self.status == self.STATUS_HALF_TIME:
            return "HT"

        elif self.status == self.STATUS_FULL_TIME:
            return "FT"

        elif self.status == self.STATUS_FIXTURE:
            return f"{self.start_time_local:%H:%M}"

        elif me is not None:
            return f"{me}'{miat}"

        else:
            return None

    @property
    @_no_match(0)
    @_override_none(0)
    def elapsed_time(self):
        time, _ = get_time_tuple(self.match.periodLabel.value)
        return time

    @property
    @_no_match(0)
    @_override_none(0)
    def added_time(self):
        _, added = get_time_tuple(self.match.periodLabel.value)
        return added

    @property
    @_no_match(False)
    def is_fixture(self):
        return self.match.status == "PreEvent"

    @property
    @_no_match(False)
    def is_live(self):
        return self.status == self.STATUS_LIVE

    @property
    @_no_match(False)
    def is_finished(self):
        return self.match.status == "PostEvent"

    @property
    @_no_match(False)
    def is_postponed(self):
        return self.match.status == "Postponed"

    @property
    @_no_match(False)
    def is_half_time(self):
        return self.status == self.STATUS_HALF_TIME

    @property
    @_no_match(False)
    def is_in_added_time(self):
        # return self.match.minutesIntoAddedTime > 0
        # TO FIX
        return False

    @property
    @_no_match(False)
    def is_penalty_shootout(self):
        return self.status == self.STATUS_PENALTIES

    @property
    @_no_match(list())
    def home_scorers(self):
        """Returns list of goalscorers for home team"""
        return self._get_goals(self.match.home)

    @property
    @_no_match("")
    def home_scorer_text(self):
        return self._format_events(self.home_scorers)

    @property
    @_no_match(list())
    def away_scorers(self):
        """Returns list of goalscorers for away team"""
        return self._get_goals(self.match.away)

    @property
    @_no_match("")
    def away_scorer_text(self):
        return self._format_events(self.away_scorers)

    @property
    @_no_match("")
    def last_goal(self):
        return self._last_event(self.ACTION_GOAL)

    @property
    @_no_match("")
    def last_home_goal(self):
        return self._last_event(self.ACTION_GOAL, just_home=True)

    @property
    @_no_match("")
    def last_away_goal(self):
        return self._last_event(self.ACTION_GOAL, just_away=True)

    @property
    @_no_match(list())
    def home_red_cards(self):
        """Returns list of players sent off for home team"""
        return self._get_reds(self.match.home)

    @property
    @_no_match(list())
    def away_red_cards(self):
        """Returns list of players sent off for away team"""
        return self._get_reds(self.match.away)

    @property
    @_no_match("")
    def last_home_red_card(self):
        return self._last_reds(just_home=True)

    @property
    @_no_match("")
    def last_away_red_card(self):
        return self._last_reds(just_away=True)

    @property
    @_no_match("")
    def last_red_card(self):
        return self._last_reds()

    def __unicode__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        Should handle accented characters.

        """
        if self.match:
            return (
                f"{self.home_team} "
                f"{self.home_score}-{self.away_score} "
                f"{self.away_team} "
                f"({self.display_time})"
            )

        else:
            return f"{self.myteam} are not playing today."

    def __str__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        """
        return self.__unicode__()

    @property
    @_no_match("")
    def start_time_local(self):
        return self.start_time_datetime.astimezone()

    @property
    @_no_match(None)
    def start_time_datetime(self):
        st = self.match.date.iso
        return datetime.fromisoformat(st)

    @property
    @_no_match(None)
    def start_time(self):
        return f"{self.start_time_local:%H:%M}"

    @property
    @_no_match(None)
    def time_to_kick_off(self):
        """Returns a timedelta object for the time until the match kicks off.

        Returns None if unable to parse match time or if match in progress.
        """
        return self.start_time_datetime - datetime.now(timezone.utc)
