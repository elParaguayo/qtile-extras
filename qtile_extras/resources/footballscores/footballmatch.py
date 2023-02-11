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

from datetime import datetime
from itertools import groupby
from typing import TYPE_CHECKING

import requests

from qtile_extras.resources.footballscores.exceptions import FSConnectionError
from qtile_extras.resources.footballscores.matchdict import MatchDict
from qtile_extras.resources.footballscores.matchdict import MatchDictKeys as MDKey
from qtile_extras.resources.footballscores.matchevent import MatchEvent
from qtile_extras.resources.footballscores.morphlinks import ML
from qtile_extras.resources.footballscores.playeraction import PlayerAction
from qtile_extras.resources.footballscores.utils import UTC

# dateutil is not part of the standard library so let's see if we can import
# and set a flag showing success or otherwise
try:
    import dateutil.parser

    HAS_DATEUTIL = True

except ImportError:
    HAS_DATEUTIL = False

if TYPE_CHECKING:
    from typing import Any


# We need a UTC timezone to do some datetime manipulations
TZ_UTZ = UTC()

API_BASE = "http://push.api.bbci.co.uk"


class FootballMatch:
    """Class for getting details of individual football matches.
    Data is pulled from BBC live scores page.
    """

    scoreslink = (
        "/proxy/data/bbc-morph-football-scores-match-list-data/"
        "endDate/{end_date}/startDate/{start_date}/{source}/"
        "version/2.4.0/withPlayerActions/{detailed}"
    )

    detailprefix = "http://www.bbc.co.uk/sport/football/live/" "partial/{id}"

    match_format = {
        "%H": "home_team",
        "%A": "away_team",
        "%h": "home_score",
        "%a": "away_score",
        "%v": "venue",
        "%T": "display_time",
        "%S": "status",
        "%R": "home_red_cards",
        "%r": "away_red_cards",
        "%G": "home_scorer_text",
        "%g": "away_scorer_text",
        "%C": "competition",
    }

    ACTION_GOAL = "goal"
    ACTION_RED_CARD = "red-card"
    ACTION_YELLOW_RED_CARD = "yellow-red-card"

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
    ):
        """Creates an instance of the Match object.
        Must be created by passing the name of one team.

        data - User can also send data to the class e.g. if multiple instances
        of class are being run thereby saving http requests. Otherwise class
        can handle request on its own.

        detailed - Do we want additional data (e.g. goal scorers, bookings)?
        """
        super(FootballMatch, self).__init__()
        self.detailed = detailed
        self.myteam = team
        self.match = MatchDict()
        self._matchdate = self._check_match_date(matchdate)

        self._on_red = on_red
        self._on_goal = on_goal
        self._on_status_change = on_status_change
        self._on_new_match = on_new_match

        self._clear_flags()

        if data is None:
            self.hasTeamPage = self._find_team_page()

            if not self.hasTeamPage:
                data = self._scan_leagues()

            else:
                self.update(first_run=events_on_first_run)

        if data:
            self.update(data=data, first_run=events_on_first_run)

    def __nonzero__(self):
        return bool(self.match)

    def __bool__(self):
        return self.__nonzero__()

    def __repr__(self):
        return "<FootballMatch('%s')>" % (self.myteam)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if any([self.match.eventKey, other.match.eventKey]):
                try:
                    return self.match.eventKey == other.match.eventKey
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

    def _request(self, url):
        url = API_BASE + url
        try:
            r = requests.get(url)
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
        raw = self._get_scores_fixtures(source=ML.MORPH_FIXTURES_ALL)

        comps = raw.get("matchData", None)

        if not comps:
            return None

        for comp in comps:
            matches = list(comp["tournamentDatesWithEvents"].values())[0][0]
            matches = matches["events"]
            for m in matches:
                if self.check_team_in_match(m):
                    return m

        return None

    def check_team_in_match(self, m):
        home = [
            m["homeTeam"]["name"][x].lower()
            for x in ["first", "full", "abbreviation", "last"]
            if m["homeTeam"]["name"][x]
        ]

        away = [
            m["awayTeam"]["name"][x].lower()
            for x in ["first", "full", "abbreviation", "last"]
            if m["awayTeam"]["name"][x]
        ]

        return self.myteam.lower() in (home + away)

    def _find_team_page(self):
        team = "-".join(self.myteam.lower().split(" "))
        teampage = "https://www.bbc.co.uk/sport/football/teams/" + team
        validteam = self.check_page(teampage)
        if validteam:
            self.myteampage = "team/{}".format(team)
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

        if source is None and self.hasTeamPage:
            source = self.myteampage

        if detailed is None:
            detailed = self.detailed

        pl = self.scoreslink.format(
            start_date=start_date,
            end_date=end_date,
            source=source,
            detailed=str(detailed).lower(),
        )

        return self._request(pl)

    def _find_match(self, payload):
        match = payload["matchData"]

        if match:
            return list(match[0]["tournamentDatesWithEvents"].values())[0][0]["events"][
                0
            ]  # noqa: E501
        else:
            return None

    def _set_callbacks(self):
        self.match.add_callback(MDKey.HOME_TEAM, self._check_home_team_event)
        self.match.add_callback(MDKey.AWAY_TEAM, self._check_away_team_event)
        self.match.add_callback(MDKey.PROGRESS, self._check_status)

    def _get_events(self, event, event_type):
        events = []

        player_actions = event.get("playerActions", list())

        for acts in player_actions:
            # player = acts["name"]["abbreviation"]
            for act in acts["actions"]:
                if act["type"] == event_type:
                    pa = PlayerAction(acts, act)
                    events.append(pa)

        return sorted(events)

    def _last_event(self, event_type, just_home=False, just_away=False):
        events = []

        if just_home and just_away:
            just_home = just_away = False

        if not just_away:
            events += self._get_events(self.match.homeTeam, event_type)

        if not just_home:
            events += self._get_events(self.match.awayTeam, event_type)

        events = sorted(events)

        if events:
            return events[-1]
        else:
            return None

    def _last_reds(self, just_home=False, just_away=False):
        reds = []
        red = self._last_event(self.ACTION_RED_CARD, just_home=just_home, just_away=just_away)
        yellow = self._last_event(
            self.ACTION_YELLOW_RED_CARD, just_home=just_home, just_away=just_away
        )

        if red:
            reds.append(red)

        if yellow:
            reds.append(yellow)

        if reds:
            return sorted(reds)[-1]
        else:
            return None

    def _get_reds(self, event):
        reds = []
        reds += self._get_events(event, self.ACTION_RED_CARD)
        reds += self._get_events(event, self.ACTION_YELLOW_RED_CARD)
        return sorted(reds)

    def _get_goals(self, event):
        return self._get_events(event, self.ACTION_GOAL)

    def _check_goal(self, old, new):
        return (old.scores.score != new.scores.score) and (new.scores.score > 0)

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
            old = self._old.homeTeam
        else:
            old = self._old.awayTeam

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
        self._statuschange = True

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
        def timesort(event):
            return (event.elapsed_time, event.added_time)

        events = sorted(events, key=lambda x: x.full_name)
        events = [list(y) for x, y in groupby(events, key=lambda x: x.full_name)]
        events = sorted(events, key=lambda x: timesort(x[0]))
        events = [sorted(x, key=timesort) for x in events]

        return events

    def _format_events(self, events):
        events = self._grouped_events(events)

        raw = []
        out = ""

        for event in events:
            name = event[0].abbreviated_name
            times = []

            if event[0].is_goal and event[0].is_own_goal:
                name = "{} (OG)".format(name)

            for item in event:
                dt = item.display_time

                if item.is_goal and item.is_penalty:
                    dt = "{} pen".format(dt)

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
            if not self.match:
                self.match = MatchDict(match, add_callbacks=True)
                self._set_callbacks()
                self._old = self.match
                self._clear_flags()
                self._matchfound = True
                if not first_run:
                    self._fire_events()

            else:
                self._clear_flags()
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
    @_no_match(str())
    def home_team(self):
        """Returns string of the home team's name"""
        return self.match.homeTeam.name.full

    @property
    @_no_match(str())
    def away_team(self):
        """Returns string of the away team's name"""
        return self.match.awayTeam.name.full

    @property
    @_no_match(int())
    @_override_none(0)
    def home_score(self):
        """Returns the number of goals scored by the home team"""
        return self.match.homeTeam.scores.score

    @property
    @_no_match(int())
    @_override_none(0)
    def away_score(self):
        """Returns the number of goals scored by the away team"""
        return self.match.awayTeam.scores.score

    @property
    @_no_match(str())
    def competition(self):
        """Returns the name of the competition to which the match belongs

        e.g. "Premier League", "FA Cup" etc

        """
        return self.match.tournamentName.full

    @property
    @_no_match(str())
    def status(self):
        """Returns the status of the match

        e.g. "L", "HT", "FT"

        """
        return self.match.eventProgress.period

    @property
    @_no_match(str())
    def long_status(self):
        return self.match.eventStatusNote

    @property
    @_no_match(str())
    def display_time(self):
        me = self.elapsed_time
        et = self.added_time

        miat = "+{}".format(et) if et else ""

        if self.is_postponed:
            return "P"

        elif self.status == self.STATUS_HALF_TIME:
            return "HT"

        elif self.status == self.STATUS_FULL_TIME:
            return "FT"

        elif self.status == self.STATUS_FIXTURE:
            return self.start_time_uk

        elif me is not None:
            return "{}{}'".format(me, miat)

        else:
            return None

    @property
    @_no_match(int())
    @_override_none(0)
    def elapsed_time(self):
        return self.match.minutesElapsed

    @property
    @_no_match(int())
    @_override_none(0)
    def added_time(self):
        return self.match.minutesIntoAddedTime

    @property
    @_no_match(str())
    def venue(self):
        return self.match.venue.name.full

    @property
    @_no_match(False)
    def is_fixture(self):
        return self.match.eventStatus == "pre-event"

    @property
    @_no_match(False)
    def is_live(self):
        return self.match.eventStatus == "mid-event" and not self.status == self.STATUS_HALF_TIME

    @property
    @_no_match(False)
    def is_half_time(self):
        return self.status == self.STATUS_HALF_TIME

    @property
    @_no_match(False)
    def is_finished(self):
        return self.match.eventStatus == "post-event"

    @property
    @_no_match(False)
    def is_in_added_time(self):
        return self.match.minutesIntoAddedTime > 0

    @property
    @_no_match(False)
    def is_postponed(self):
        return self.match.eventStatus == "postponed"

    @property
    @_no_match(list())
    def home_scorers(self):
        """Returns list of goalscorers for home team"""
        return self._get_goals(self.match.homeTeam)

    @property
    @_no_match(str())
    def home_scorer_text(self):
        return self._format_events(self.home_scorers)

    @property
    @_no_match(list())
    def away_scorers(self):
        """Returns list of goalscorers for away team"""
        return self._get_goals(self.match.awayTeam)

    @property
    @_no_match(str())
    def away_scorer_text(self):
        return self._format_events(self.away_scorers)

    @property
    @_no_match(str())
    def last_goal(self):
        return self._last_event(self.ACTION_GOAL)

    @property
    @_no_match(str())
    def last_home_goal(self):
        return self._last_event(self.ACTION_GOAL, just_home=True)

    @property
    @_no_match(str())
    def last_away_goal(self):
        return self._last_event(self.ACTION_GOAL, just_away=True)

    @property
    @_no_match(list())
    def home_red_cards(self):
        """Returns list of players sent off for home team"""
        return self._get_reds(self.match.homeTeam)

    @property
    @_no_match(list())
    def away_red_cards(self):
        """Returns list of players sent off for away team"""
        return self._get_reds(self.match.awayTeam)

    @property
    @_no_match(str())
    def last_home_red_card(self):
        return self._last_reds(just_home=True)

    @property
    @_no_match(str())
    def last_away_red_card(self):
        return self._last_reds(just_away=True)

    @property
    @_no_match(str())
    def last_red_card(self):
        return self._last_reds()

    def __unicode__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        Should handle accented characters.

        """
        if self.match:
            return "%s %s-%s %s (%s)" % (
                self.home_team,
                self.home_score,
                self.away_score,
                self.away_team,
                self.display_time,
            )

        else:
            return "%s are not playing today." % (self.myteam)

    def __str__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        """
        return self.__unicode__()

    @property
    @_no_match(str())
    def start_time_uk(self):
        return self.match.startTimeInUKHHMM

    @property
    @_no_match(None)
    def start_time_datetime(self):
        st = self.match.startTime

        if HAS_DATEUTIL:
            try:
                return dateutil.parser.parse(st)

            except ValueError:
                return None

        else:
            return None

    @property
    @_no_match(None)
    def start_time(self):
        return self.match.startTime

    @property
    @_no_match(None)
    def time_to_kick_off(self):
        """Returns a timedelta object for the time until the match kicks off.

        Returns None if unable to parse match time or if match in progress.
        """
        if HAS_DATEUTIL and self.is_fixture:
            return self.start_time_datetime.astimezone(TZ_UTZ) - datetime.now(TZ_UTZ)

        else:
            return None
