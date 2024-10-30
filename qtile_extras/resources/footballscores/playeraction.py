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
from qtile_extras.resources.footballscores.utils import get_time_tuple

ACTION_GOAL = "goal"
ACTION_RED_CARD = "card"
ACTION_YELLOW_RED_CARD = "yellow-red-card"

actions = {ACTION_GOAL: "GOAL", ACTION_RED_CARD: "RED CARD", ACTION_YELLOW_RED_CARD: "RED CARD"}


class PlayerAction:
    def __init__(self, player, action):
        if not isinstance(player, dict):
            player = dict()

        self._name = player.get("playerName", "")

        if not isinstance(action, dict):
            action = dict()

        self._actiontype = player.get("actionType", None)
        self._actiontime = action.get("timeLabel", dict()).get("value", "0'")
        self._time_tuple = get_time_tuple(self._actiontime)
        act_type = action.get("type", "")
        self._actionowngoal = act_type == "Own Goal"
        self._actionpenalty = act_type == "Penalty"
        self._actionsecondyellow = act_type == "Two Yellow Cards"

    @classmethod
    def get_all(cls, actions):
        return [cls(actions, action) for action in actions["actions"]]

    def __lt__(self, other):
        return self._time_tuple < other._time_tuple

    def __eq__(self, other):
        return self._time_tuple == other._time_tuple

    def __repr__(self):
        return "<{}: {} ({})>".format(
            actions[self._actiontype],
            self.name.encode("ascii", "replace"),
            self._actiontime,
        )

    @property
    def name(self):
        return self._name

    @property
    def action_type(self):
        return self._actiontype

    @property
    def display_time(self):
        return self._actiontime

    @property
    def elapsed_time(self):
        return self._time_tuple[0]

    @property
    def added_time(self):
        return self._time_tuple[1]

    @property
    def is_goal(self):
        return self._actiontype == ACTION_GOAL

    @property
    def is_red_card(self):
        return self._actiontype == ACTION_RED_CARD

    @property
    def is_straight_red(self):
        return self._actiontype == ACTION_RED_CARD and not self._actionsecondyellow

    @property
    def is_second_booking(self):
        return self._actionsecondyellow

    @property
    def is_penalty(self):
        return self._actionpenalty

    @property
    def is_own_goal(self):
        return self._actionowngoal
