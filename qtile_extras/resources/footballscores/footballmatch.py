from datetime import datetime
from itertools import groupby
import json
import requests

from .base import matchcommon
from .exceptions import FSConnectionError
from .matchdict import MatchDict
from .matchdict import MatchDictKeys as MDKey
from .matchevent import MatchEvent
from .playeraction import PlayerAction
from .utils import UTC
from .morphlinks import ML

# dateutil is not part of the standard library so let's see if we can import
# and set a flag showing success or otherwise
try:
    import dateutil.parser
    HAS_DATEUTIL = True

except ImportError:
    HAS_DATEUTIL = False


# We need a UTC timezone to do some datetime manipulations
TZ_UTZ = UTC()

API_BASE = "http://push.api.bbci.co.uk"


class FootballMatch(matchcommon):
    '''Class for getting details of individual football matches.
    Data is pulled from BBC live scores page.
    '''
    scoreslink = ("/proxy/data/bbc-morph-football-scores-match-list-data/"
                  "endDate/{end_date}/startDate/{start_date}/{source}/"
                  "version/2.4.0/withPlayerActions/{detailed}")

    detailprefix = ("http://www.bbc.co.uk/sport/football/live/"
                    "partial/{id}")

    match_format = {"%H": "HomeTeam",
                    "%A": "AwayTeam",
                    "%h": "HomeScore",
                    "%a": "AwayScore",
                    "%v": "Venue",
                    "%T": "DisplayTime",
                    "%S": "Status",
                    "%R": "HomeRedCards",
                    "%r": "AwayRedCards",
                    "%G": "HomeScorerText",
                    "%g": "AwayScorerText",
                    "%C": "Competition"}

    ACTION_GOAL = "goal"
    ACTION_RED_CARD = "red-card"
    ACTION_YELLOW_RED_CARD = "yellow-red-card"

    STATUS_HALF_TIME = "HALFTIME"
    STATUS_FULL_TIME = "FULLTIME"
    STATUS_FIXTURE = "FIXTURE"
    STATUS_ET_FIRST_HALF = "EXTRATIMEFIRSTHALF"
    STATUS_ET_HALF_TIME = "EXTRATIMEHALFTIME"

    def __init__(self, team, detailed=True, data=None, on_goal=None,
                 on_red=None, on_status_change=None, on_new_match=None,
                 matchdate=None, events_on_first_run=False):
        '''Creates an instance of the Match object.
        Must be created by passing the name of one team.

        data - User can also send data to the class e.g. if multiple instances
        of class are being run thereby saving http requests. Otherwise class
        can handle request on its own.

        detailed - Do we want additional data (e.g. goal scorers, bookings)?
        '''
        super(FootballMatch, self).__init__()
        self.detailed = detailed
        self.myteam = team
        self.match = MatchDict()
        self._matchdate = self._check_match_date(matchdate)

        self._on_red = on_red
        self._on_goal = on_goal
        self._on_status_change = on_status_change
        self._on_new_match = on_new_match

        self._clearFlags()

        if data is None:
            self.hasTeamPage = self._findTeamPage()

            if not self.hasTeamPage:
                data = self._scanLeagues()

            else:
                self.update(first_run=events_on_first_run)

        if data:
            self.update(data=data, first_run=events_on_first_run)

    def __nonzero__(self):

        return bool(self.match)

    def __bool__(self):

        return self.__nonzero__()

    def __repr__(self):

        return "<FootballMatch(\'%s\')>" % (self.myteam)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            try:
                return self.match.eventKey == other.match.eventKey
            except AttributeError:
                return self.myteam == other.myteam
        else:
            return False

    # Semi-hidden methods, only meant to be called by other class methods

    def _no_match(default):
        """
        Decorator to provide default values for properties when there is no
        match found.

        e.g.:
            @property
            @_no_match(str())
            def HomeTeam(self):
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

    def _override_none(value):
        """
        Decorator to provide default values for properties when there is no
        current value.

        For example, this decorator can be used to convert a None value for a
        match score (empty before the match starts) to 0.

        e.g.:
            @property
            @_no_match(int())
            @_override_none(0)
            def HomeScore(self):
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

    def _dump(self, filename):

        c = {k: v for k, v in self.match.iteritems() if k != "_callbacks"}

        with open(filename, "w") as f:
            json.dump(c, f, indent=4)

    def _request(self, url):
        url = API_BASE + url
        try:
            r = requests.get(url)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            raise FSConnectionError

        if r.status_code == 200:
            return r.json()
        else:
            return dict()

    def _check_match_date(self, matchdate):

        if matchdate is None:
            return None

        try:
            datetime.strptime(matchdate, "%Y-%m-%d")
            return matchdate

        except (ValueError, TypeError):
            raise ValueError("Invalid match date. "
                             "Match date format must by YYYY-MM-DD.")

    def _canUpdate(self):

        return self.hasTeamPage

    def _scanLeagues(self):

        raw = self._getScoresFixtures(source=ML.MORPH_FIXTURES_ALL)

        comps = raw.get("matchData", None)

        if not comps:
            return Nonce

        for comp in comps:
            matches = list(comp["tournamentDatesWithEvents"].values())[0][0]
            matches = matches["events"]
            for m in matches:
                if self.checkTeamInMatch(m):
                    return m

        return None

    def checkTeamInMatch(self, m):
        home = [m["homeTeam"]["name"][x].lower()
                    for x in ["first", "full", "abbreviation", "last"]
                    if m["homeTeam"]["name"][x]]

        away = [m["awayTeam"]["name"][x].lower()
                    for x in ["first", "full", "abbreviation", "last"]
                    if m["awayTeam"]["name"][x]]

        return self.myteam.lower() in (home + away)


    def _findTeamPage(self):
        team = "-".join(self.myteam.lower().split(" "))
        teampage = "https://www.bbc.co.uk/sport/football/teams/" + team
        validteam = self.checkPage(teampage)
        if validteam:
            self.myteampage = "team/{}".format(team)
            return True
        else:
            return False

    def _getScoresFixtures(self, start_date=None, end_date=None,
                           source=None, detailed=None):
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

        pl = self.scoreslink.format(start_date=start_date,
                                    end_date=end_date,
                                    source=source,
                                    detailed=str(detailed).lower())

        return self._request(pl)

    def _findMatch(self, payload):
        match = payload["matchData"]

        if match:
            return list(match[0]["tournamentDatesWithEvents"].values())[0][0]["events"][0]  # noqa: E501
        else:
            return None

    def _setCallbacks(self):
        self.match.add_callback(MDKey.HOME_TEAM, self._checkHomeTeamEvent)
        self.match.add_callback(MDKey.AWAY_TEAM, self._checkAwayTeamEvent)
        self.match.add_callback(MDKey.PROGRESS, self._checkStatus)

    def _getEvents(self, event, event_type):
        events = []

        player_actions = event.get("playerActions", list())

        for acts in player_actions:
            # player = acts["name"]["abbreviation"]
            for act in acts["actions"]:
                if act["type"] == event_type:
                    pa = PlayerAction(acts, act)
                    events.append(pa)

        return sorted(events)

    def _lastEvent(self, event_type, just_home=False, just_away=False):
        events = []

        if just_home and just_away:
            just_home = just_away = False

        if not just_away:
            events += self._getEvents(self.match.homeTeam, event_type)

        if not just_home:
            events += self._getEvents(self.match.awayTeam, event_type)

        events = sorted(events)

        if events:
            return events[-1]
        else:
            return None

    def _lastReds(self, just_home=False, just_away=False):

        reds = []
        red = self._lastEvent(self.ACTION_RED_CARD,
                              just_home=just_home,
                              just_away=just_away)
        yellow = self._lastEvent(self.ACTION_YELLOW_RED_CARD,
                                 just_home=just_home,
                                 just_away=just_away)

        if red:
            reds.append(red)

        if yellow:
            reds.append(yellow)

        if reds:
            return sorted(reds)[-1]
        else:
            return None

    def _getReds(self, event):
        reds = []
        reds += self._getEvents(event, self.ACTION_RED_CARD)
        reds += self._getEvents(event, self.ACTION_YELLOW_RED_CARD)
        return sorted(reds)

    def _getGoals(self, event):
        return self._getEvents(event, self.ACTION_GOAL)

    def _checkGoal(self, old, new):
        return ((old.scores.score != new.scores.score)
                and (new.scores.score > 0))

    def _checkRed(self, old, new):

        old_reds = self._getReds(old)
        new_reds = self._getReds(new)

        return old_reds != new_reds

    def _checkHomeTeamEvent(self, event):
        self._checkTeamEvent(event, home=True)

    def _checkAwayTeamEvent(self, event):
        self._checkTeamEvent(event, home=False)

    def _checkTeamEvent(self, event, home=True):

        if home:
            old = self._old.homeTeam
        else:
            old = self._old.awayTeam

        new = MatchDict(event)

        goal = self._checkGoal(old, new)
        red = self._checkRed(old, new)

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

    def _checkStatus(self, status):
        self._statuschange = True

    def _clearFlags(self):
        self._homegoal = False
        self._awaygoal = False
        self._homered = False
        self._awayred = False
        self._statuschange = False
        self._matchfound = False

    def _fireEvent(self, func, payload):

        try:
            func(payload)
        except TypeError:
            pass

    def _fireEvents(self):

        if self._homegoal:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_GOAL, self, True)
            self._fireEvent(func, payload)

        if self._awaygoal:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_GOAL, self, False)
            self._fireEvent(func, payload)

        if self._homered:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_RED_CARD, self, True)
            self._fireEvent(func, payload)

        if self._awayred:
            func = self.on_goal
            payload = MatchEvent(MatchEvent.TYPE_RED_CARD, self, False)
            self._fireEvent(func, payload)

        if self._statuschange:
            func = self.on_status_change
            payload = MatchEvent(MatchEvent.TYPE_STATUS, self)
            self._fireEvent(func, payload)

        if self._matchfound:
            func = self.on_new_match
            payload = MatchEvent(MatchEvent.TYPE_NEW_MATCH, self)
            self._fireEvent(func, payload)

    def _groupedEvents(self, events):

        def timesort(event):
            return (event.ElapsedTime, event.AddedTime)

        events = sorted(events, key=lambda x: x.FullName)
        events = [list(y) for x, y in groupby(events,
                                              key=lambda x: x.FullName)]
        events = sorted(events, key=lambda x: timesort(x[0]))
        events = [sorted(x, key=timesort) for x in events]

        return events

    def _formatEvents(self, events):

        events = self._groupedEvents(events)

        raw = []
        out = u""

        for event in events:

            name = event[0].AbbreviatedName
            times = []

            if event[0].isGoal and event[0].isOwnGoal:
                name = u"{} (OG)".format(name)

            for item in event:
                dt = item.DisplayTime

                if item.isGoal and item.isPenalty:
                    dt = u"{} pen".format(dt)

                times.append(dt)

            raw.append((name, times))

        for i, (player, events) in enumerate(raw):

            out += player
            ev = u" ("
            ev += u", ".join(events)
            ev += u")"

            out += ev

            if i < len(raw) - 1:
                out += u", "

        return out

    def formatText(self, text):
        values = {k[1]: getattr(self, v) for k, v in self.match_format.items()}
        return text.format(**values)

    def formatMatch(self, fmt):

        for key in self.match_format:
            try:
                fmt = fmt.replace(key, getattr(self, self.match_format[key]))
            except TypeError:
                fmt = fmt.replace(key,
                                  str(getattr(self, self.match_format[key])))

        return fmt

    def formatTimeToKickOff(self, fmt):

        ko = self.TimeToKickOff

        if ko is None:
            return ""

        d = {"d": ko.days}
        d["h"], rem = divmod(ko.seconds, 3600)
        d["m"], d["s"] = divmod(rem, 60)
        d["s"] = int(d["s"])

        return fmt.format(**d)

    def update(self, data=None, first_run=False):

        if data is None and not self._canUpdate():
            data = self._scanLeagues()

        elif data is None:
            rawdata = self._getScoresFixtures()
            if rawdata:
                match = self._findMatch(rawdata)
            else:
                match = None

        if data:
            match = data

        if match:

            if not self.match:
                self.match = MatchDict(match, add_callbacks=True)
                self._setCallbacks()
                self._old = self.match
                self._clearFlags()
                self._matchfound = True
                if not first_run:
                    self._fireEvents()

            else:
                self._clearFlags()
                self.match.update(match)
                if not first_run:
                    self._fireEvents()
                self._old = self.match

            return True

        # Need this to clear the match if no data (e.g. next day)
        elif match is None and self.match:
            self._clearFlags()
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
    def HomeTeam(self):
        """Returns string of the home team's name

        """
        return self.match.homeTeam.name.full

    @property
    @_no_match(str())
    def AwayTeam(self):
        """Returns string of the away team's name

        """
        return self.match.awayTeam.name.full

    @property
    @_no_match(int())
    @_override_none(0)
    def HomeScore(self):
        """Returns the number of goals scored by the home team

        """
        return self.match.homeTeam.scores.score

    @property
    @_no_match(int())
    @_override_none(0)
    def AwayScore(self):
        """Returns the number of goals scored by the away team

        """
        return self.match.awayTeam.scores.score

    @property
    @_no_match(str())
    def Competition(self):
        """Returns the name of the competition to which the match belongs

        e.g. "Premier League", "FA Cup" etc

        """
        return self.match.tournamentName.full

    @property
    @_no_match(str())
    def Status(self):
        """Returns the status of the match

        e.g. "L", "HT", "FT"

        """
        return self.match.eventProgress.period

    @property
    @_no_match(str())
    def LongStatus(self):

        return self.match.eventStatusNote

    @property
    @_no_match(str())
    def DisplayTime(self):
        me = self.ElapsedTime
        et = self.AddedTime

        miat = u"+{}".format(et) if et else ""

        if self.isPostponed:
            return u"P"

        elif self.Status == self.STATUS_HALF_TIME:
            return u"HT"

        elif self.Status == self.STATUS_FULL_TIME:
            return u"FT"

        elif self.Status == self.STATUS_FIXTURE:
            return self.StartTimeUK

        elif me is not None:
            return u"{}{}'".format(me, miat)

        else:
            return None

    @property
    @_no_match(int())
    @_override_none(0)
    def ElapsedTime(self):
        return self.match.minutesElapsed

    @property
    @_no_match(int())
    @_override_none(0)
    def AddedTime(self):
        return self.match.minutesIntoAddedTime

    @property
    @_no_match(str())
    def Venue(self):
        return self.match.venue.name.full

    @property
    @_no_match(False)
    def isFixture(self):
        return self.match.eventStatus == "pre-event"

    @property
    @_no_match(False)
    def isLive(self):
        return (self.match.eventStatus == "mid-event" and
                not self.Status == self.STATUS_HALF_TIME)

    @property
    @_no_match(False)
    def isHalfTime(self):
        return self.Status == self.STATUS_HALF_TIME

    @property
    @_no_match(False)
    def isFinished(self):
        return self.match.eventStatus == "post-event"

    @property
    @_no_match(False)
    def isInAddedTime(self):
        return self.match.minutesIntoAddedTime > 0

    @property
    @_no_match(False)
    def isPostponed(self):
        return self.match.eventStatus == "postponed"

    @property
    @_no_match(list())
    def HomeScorers(self):
        """Returns list of goalscorers for home team

        """
        return self._getGoals(self.match.homeTeam)

    @property
    @_no_match(str())
    def HomeScorerText(self):
        return self._formatEvents(self.HomeScorers)

    @property
    @_no_match(list())
    def AwayScorers(self):
        """Returns list of goalscorers for away team

        """
        return self._getGoals(self.match.awayTeam)

    @property
    @_no_match(str())
    def AwayScorerText(self):
        return self._formatEvents(self.AwayScorers)

    @property
    @_no_match(str())
    def LastGoal(self):
        return self._lastEvent(self.ACTION_GOAL)

    @property
    @_no_match(str())
    def LastHomeGoal(self):
        return self._lastEvent(self.ACTION_GOAL, just_home=True)

    @property
    @_no_match(str())
    def LastAwayGoal(self):
        return self._lastEvent(self.ACTION_GOAL, just_away=True)

    @property
    @_no_match(list())
    def HomeRedCards(self):
        """Returns list of players sent off for home team

        """
        return self._getReds(self.match.homeTeam)

    @property
    @_no_match(list())
    def AwayRedCards(self):
        """Returns list of players sent off for away team

        """
        return self._getReds(self.match.awayTeam)

    @property
    @_no_match(str())
    def LastHomeRedCard(self):
        return self._lastReds(just_home=True)

    @property
    @_no_match(str())
    def LastAwayRedCard(self):
        return self._lastReds(just_away=True)

    @property
    @_no_match(str())
    def LastRedCard(self):
        return self._lastReds()

    def __unicode__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        Should handle accented characters.

        """
        if self.match:

            return u"%s %s-%s %s (%s)" % (
                                          self.HomeTeam,
                                          self.HomeScore,
                                          self.AwayScore,
                                          self.AwayTeam,
                                          self.DisplayTime
                                          )

        else:

            return u"%s are not playing today." % (self.myteam)

    def __str__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        """
        return self.__unicode__()

    @property
    @_no_match(str())
    def StartTimeUK(self):

        return self.match.startTimeInUKHHMM

    @property
    @_no_match(None)
    def StartTimeDatetime(self):

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
    def StartTime(self):

        return self.match.startTime

    @property
    @_no_match(None)
    def TimeToKickOff(self):
        '''Returns a timedelta object for the time until the match kicks off.

        Returns None if unable to parse match time or if match in progress.
        '''
        if HAS_DATEUTIL and self.isFixture:
            return (self.StartTimeDatetime.astimezone(TZ_UTZ)
                    - datetime.now(TZ_UTZ))

        else:
            return None
