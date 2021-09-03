from datetime import datetime

import requests

from .base import matchcommon
from .footballmatch import FootballMatch

API_BASE = "http://push.api.bbci.co.uk"


class League(matchcommon):

    leaguelink = ("/proxy/data/bbc-morph-football-scores-match-list-data/"
                  "endDate/{end_date}/startDate/{start_date}/"
                  "tournament/{tournament}/"
                  "withPlayerActions/{detailed}/"
                  "version/2.4.0")

    def __init__(self, league, detailed=False, on_goal=None,
                 on_red=None, on_status_change=None, on_new_match=None):
        super(League, self).__init__()
        self.league = league
        self.matches = []
        self.detailed = detailed
        self.on_goal = on_goal
        self.on_red = on_red
        self.on_status_change = on_status_change
        self.on_new_match = on_new_match
        self._setup()

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index < len(self.matches):
            m = self.matches[self.index]
            self.index += 1
            return m
        else:
            raise StopIteration

    def __len__(self):
        return len(self.matches)

    def __getitem__(self, index):
        return self.matches[index]

    def __nonzero__(self):

        return bool(self.matches)

    def __bool__(self):

        return self.__nonzero__()

    def _setup(self):
        lg = "-".join(self.league.lower().split(" "))
        self.leagueid = lg
        if self.leagueid:
            self.matches = self.getMatches()

    def _request(self, url):
        url = API_BASE + url
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        else:
            return dict()

    def findleague(self, league):
        leagues = self.getTournaments()
        if leagues:
            for lg in leagues:
                if lg["name"].lower() == league.lower():
                    return lg["url"].split("/")[3]

        return None

    def _getScoresFixtures(self, start_date=None, end_date=None,
                           source=None, detailed=None):
        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if source is None and self.leagueid:
            source = self.leagueid

        if detailed is None:
            detailed = self.detailed

        pl = self.leaguelink.format(start_date=start_date,
                                    end_date=end_date,
                                    tournament=source,
                                    detailed=str(detailed).lower())

        return self._request(pl)

    def _getRawData(self):
        rawdata = self._getScoresFixtures()
        if not rawdata:
            return []

        if not rawdata.get("matchData"):
            return []

        data = rawdata["matchData"][0]["tournamentDatesWithEvents"]

        mdata = []
        for event in list(data.values())[0]:
            mdata += event["events"]

        return mdata

    def getMatches(self):

        matches = []

        data = self._getRawData()

        for m in data:
            home = m["homeTeam"]["name"]["abbreviation"]
            fmatch = FootballMatch(home,
                                   data=m,
                                   detailed=self.detailed,
                                   on_goal=self.on_goal,
                                   on_red=self.on_red,
                                   on_status_change=self.on_status_change,
                                   on_new_match=self.on_new_match)
            matches.append(fmatch)

        return matches

    def _update(self):
        data = self._getRawData()

        for m in data:
            home = m["homeTeam"]["name"]["abbreviation"]
            for team in self.matches:
                if team.myteam == home:
                    team.update(data=m)
                    break

    def update(self):

        if not self.leagueid:
            self._setup()

        matches = self.getMatches()

        current = [x for x in self.matches if x in matches]
        current += [x for x in matches if x not in self.matches]

        self.matches = current

        if self.matches:
            self._update()

    @property
    def LeagueName(self):
        if not self.matches:
            return self.league

        return self.matches[0].Competition
