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
    def is_red(self):
        return self.eventType == self.TYPE_RED_CARD

    @property
    def is_goal(self):
        return self.eventType == self.TYPE_GOAL

    @property
    def is_status_change(self):
        return self.eventType == self.TYPE_STATUS

    @property
    def is_new_match(self):
        return self.eventType == self.TYPE_NEW_MATCH

    @property
    def is_live(self):
        return self.match.is_live

    @property
    def is_fixture(self):
        return self.match.is_fixture

    @property
    def is_finished(self):
        return self.match.is_finished

    @property
    def scorer(self):
        if self.is_goal:
            if self.home:
                return self.match.last_home_goal
            else:
                return self.match.last_away_goal

    @property
    def red_card(self):
        if self.is_red:
            if self.home:
                return self.match.last_home_red_card
            else:
                return self.match.last_away_red_card
