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
ACTION_GOAL = "goal"
ACTION_RED_CARD = "red-card"
ACTION_YELLOW_RED_CARD = "yellow-red-card"

actions = {ACTION_GOAL: "GOAL", ACTION_RED_CARD: "RED CARD", ACTION_YELLOW_RED_CARD: "RED CARD"}


class PlayerAction(object):
    def __init__(self, player, action):
        if not isinstance(player, dict):
            player = dict()

        nm = player.get("name", dict())
        self._fullname = nm.get("full", "")
        self._abbreviatedname = nm.get("abbreviation", "")
        self._firstname = nm.get("first", "")
        self._lastname = nm.get("last", "")

        if not isinstance(action, dict):
            action = dict()

        self._actiontype = action.get("type", None)
        self._actiondisplaytime = action.get("displayTime", None)
        self._actiontime = action.get("timeElapsed", 0)
        self._actionaddedtime = action.get("addedTime", 0)
        self._actionowngoal = action.get("ownGoal", False)
        self._actionpenalty = action.get("penalty", False)

    def __lt__(self, other):
        normal = self._actiontime < other._actiontime
        added = (self._actiontime == other._actiontime) and (
            self._actionaddedtime < other._actionaddedtime
        )
        return normal or added

    def __eq__(self, other):
        normal = self._actiontime == other._actiontime
        added = self._actionaddedtime == other._actionaddedtime
        return normal and added

    def __repr__(self):
        return "<{}: {} ({})>".format(
            actions[self._actiontype],
            self._abbreviatedname.encode("ascii", "replace"),
            self._actiondisplaytime,
        )

    @property
    def full_name(self):
        return self._fullname

    @property
    def first_name(self):
        return self._firstname

    @property
    def last_name(self):
        return self._lastname

    @property
    def abbreviated_name(self):
        return self._abbreviatedname

    @property
    def action_type(self):
        return self._actiontype

    @property
    def display_time(self):
        return self._actiondisplaytime

    @property
    def elapsed_time(self):
        return self._actiontime

    @property
    def added_time(self):
        return self._actionaddedtime

    @property
    def is_goal(self):
        return self._actiontype == ACTION_GOAL

    @property
    def is_red_card(self):
        return self._actiontype == ACTION_RED_CARD or self._actiontype == ACTION_YELLOW_RED_CARD

    @property
    def is_straight_red(self):
        return self._actiontype == ACTION_RED_CARD

    @property
    def is_second_booking(self):
        return self._actiontype == ACTION_YELLOW_RED_CARD

    @property
    def is_penalty(self):
        return self._actionpenalty

    @property
    def is_own_goal(self):
        return self._actionowngoal
