class MatchEvent(object):

    TYPE_GOAL = "GOAL"
    TYPE_RED_CARD = "RED"
    TYPE_STATUS = "STATUS"
    TYPE_NEW_MATCH = "NEW"

    def __init__(self, event_type, match, home=None):
        self.eventType = event_type
        self.home = home
        self.match = match

    @property
    def isRed(self):
        return self.eventType == self.TYPE_RED_CARD

    @property
    def isGoal(self):
        return self.eventType == self.TYPE_GOAL

    @property
    def isStatusChange(self):
        return self.eventType == self.TYPE_STATUS

    @property
    def isNewMatch(self):
        return self.eventType == self.TYPE_NEW_MATCH

    @property
    def isLive(self):
        return self.match.isLive

    @property
    def isFixture(self):
        return self.match.isFixture

    @property
    def isFinished(self):
        return self.match.isFinished

    @property
    def Scorer(self):

        if self.isGoal:
            if self.home:
                return self.match.LastHomeGoal
            else:
                return self.match.LastAwayGoal

    @property
    def RedCard(self):

        if self.isRed:
            if self.home:
                return self.match.LastHomeRedCard
            else:
                return self.match.LastAwayRedCard
