class MatchDictKeys(object):
    AWAY_TEAM = 'awayTeam'
    COMMENT = 'comment'
    CPS_ID = 'cpsId'
    CPS_LIVE = 'cpsLive'
    EVENT_KEY = 'eventKey'
    EVENT_STATUS = 'eventStatus'
    EVENT_STATUS_NOTE = 'eventStatusNote'
    EVENT_TYPE = 'eventType'
    HOME_TEAM = 'homeTeam'
    HREF = 'href'
    MINS_ELAPSED = 'minutesElapsed'
    MINS_EXTRA_TIME = 'minutesIntoAddedTime'
    OFFICIALS = 'officials'
    OUTCOME_TYPE = 'eventOutcomeType'
    PROGRESS = 'eventProgress'
    SERIES_WINNER = 'seriesWinner'
    START_TIME = 'startTime'
    START_TIME_UKHHMM = 'startTimeInUKHHMM'
    STATUS_REASON = 'eventStatusReason'
    TOURNAMENT = 'tournamentSlug'
    TOURNAMENT_INFO = 'tournamentInfo'
    TOURNAMENT_NAME = 'tournamentName'
    VENUE = 'venue'


class MatchDict(dict):
    """Class definition to turn JSON response into class object where match
       information is available as class attributes.

       Callbacks are available for top level changes.
    """
    def __init__(self, *args, **kwargs):
        cb = kwargs.pop('add_callbacks', False)
        self.update(*args, **kwargs)
        self.__dict__ = self
        if cb:
            self._callbacks = {}

    def __getattr__(self, name):
        if name not in self:
            return None

    def __setitem__(self, item, value):
        try:
            if self[item] and value != self[item]:
                for cb in [x for x in self._callbacks[item]
                           if item in self._callbacks]:
                    cb(value)

        except KeyError:
            pass

        if type(value) == dict:
            value = MatchDict(value)

        super(MatchDict, self).__setitem__(item, value)

    def add_callback(self, key, callback):
        if key in self._callbacks:
            self._callbacks[key].append(callback)

        else:
            self._callbacks[key] = [callback]

    def remove_callbacks(self, key):
        self._callbacks.pop(key)

    def remove_callback(self, key, callback):
        if key in self._callbacks:
            while callback in self._callbacks[key]:
                self._callbacks[key].remove(callback)

    def update(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, "
                                "got %d" % len(args))
            other = dict(args[0])
            for key in other:
                self[key] = other[key]
        for key in kwargs:
            self[key] = kwargs[key]
