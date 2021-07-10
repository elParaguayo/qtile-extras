ACTION_GOAL = "goal"
ACTION_RED_CARD = "red-card"
ACTION_YELLOW_RED_CARD = "yellow-red-card"

actions = {ACTION_GOAL: "GOAL",
           ACTION_RED_CARD: "RED CARD",
           ACTION_YELLOW_RED_CARD: "RED CARD"}


class PlayerAction(object):

    def __init__(self, player, action):

        if not type(player) == dict:
            player = dict()

        nm = player.get("name", dict())
        self._fullname = nm.get("full", u"")
        self._abbreviatedname = nm.get("abbreviation", u"")
        self._firstname = nm.get("first", u"")
        self._lastname = nm.get("last", u"")

        if not type(action) == dict:
            action = dict()

        self._actiontype = action.get("type", None)
        self._actiondisplaytime = action.get("displayTime", None)
        self._actiontime = action.get("timeElapsed", 0)
        self._actionaddedtime = action.get("addedTime", 0)
        self._actionowngoal = action.get("ownGoal", False)
        self._actionpenalty = action.get("penalty", False)

    def __lt__(self, other):
        normal = self._actiontime < other._actiontime
        added = ((self._actiontime == other._actiontime) and
                 (self._actionaddedtime < other._actionaddedtime))
        return normal or added

    def __eq__(self, other):
        normal = self._actiontime == other._actiontime
        added = self._actionaddedtime == other._actionaddedtime
        return normal and added

    def __repr__(self):
        return "<{}: {} ({})>".format(actions[self._actiontype],
                                      self._abbreviatedname.encode("ascii",
                                                                   "replace"),
                                      self._actiondisplaytime)

    @property
    def FullName(self):
        return self._fullname

    @property
    def FirstName(self):
        return self._firstname

    @property
    def LastName(self):
        return self._lastname

    @property
    def AbbreviatedName(self):
        return self._abbreviatedname

    @property
    def ActionType(self):
        return self._actiontype

    @property
    def DisplayTime(self):
        return self._actiondisplaytime

    @property
    def ElapsedTime(self):
        return self._actiontime

    @property
    def AddedTime(self):
        return self._actionaddedtime

    @property
    def isGoal(self):
        return self._actiontype == ACTION_GOAL

    @property
    def isRedCard(self):
        return (self._actiontype == ACTION_RED_CARD or
                self._actiontype == ACTION_YELLOW_RED_CARD)

    @property
    def isStraightRed(self):
        return self._actiontype == ACTION_RED_CARD

    @property
    def isSecondBooking(self):
        return self._actiontype == ACTION_YELLOW_RED_CARD

    @property
    def isPenalty(self):
        return self._actionpenalty

    @property
    def isOwnGoal(self):
        return self._actionowngoal
