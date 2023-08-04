# Copyright (c) 2016-21 elParaguayo
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
import datetime
import json
import os
import pickle
import time

from pint import Unit
from stravalib import Client
from stravalib.model import Activity

from qtile_extras.resources.stravadata.locations import AUTH, CACHE, CREDS, TIMESTAMP

NUM_EVENTS = 5

APP_ID = AUTH.get("id", False)
SECRET = AUTH.get("secret", False)

SHOW_EXTRA_MONTHS = 5

KM = Unit("km")


class ActivityHistory(object):
    def __init__(self):
        self.current = None
        self.previous = []
        self.year = None
        self.alltime = None

    def add_month(self, actsum):
        self.previous.append(actsum)


class ActivitySummary(object):
    def __init__(self, distance_unit=KM, groupdate=None, child=False):
        self.activities = []
        self.distance_unit = distance_unit
        self.dist = distance_unit * 0
        self.time = 0
        self._date = datetime.datetime.now()
        self.groupdate = groupdate
        self.paceformat = "{min:2.0f}:{sec:02.0f}"
        self.timeformat = "{hr:0d}:{min:02d}:{sec:02d}"
        self.child = child
        self.children = []
        self._name = ""

    @classmethod
    def from_activity(cls, activity, distance_unit=KM, child=False):
        act = cls(distance_unit=distance_unit, child=child)
        act.add_activity(activity)
        return act

    @classmethod
    def from_activities(cls, activities, distance_unit=KM, child=False):
        act = cls(distance_unit=distance_unit, child=child)
        act.add_activities(activities)
        return act

    def _is_activity(self, activity):
        return isinstance(activity, Activity) and activity.type == "Run"

    def create_child(self, activity):
        if not self.child:
            self.children.append(ActivitySummary.from_activity(activity, child=True))

    def add_activity(self, activity):
        if self._is_activity(activity):
            self.activities.append(activity)
            if not self.is_multi_activity:
                self._date = activity.start_date_local
                self._name = activity.name

            self.dist += activity.distance
            self.time += activity.moving_time.total_seconds()

            self.create_child(activity)

    def add_activities(self, activities):
        for act in activities:
            self.add_activity(act)

    @property
    def is_multi_activity(self):
        return len(self.activities) > 1

    @property
    def pace(self):
        if self.distance > 0:
            pace = self.time / self.distance
        else:
            pace = 0
        m, s = divmod(pace, 60)
        return (int(m), int(s))

    @property
    def distance(self):
        return self.dist.magnitude

    @property
    def format_pace(self):
        min, sec = self.pace
        return self.paceformat.format(min=min, sec=sec)

    @property
    def format_time(self):
        return self.timeformat.format(hr=self.hours, min=self.mins, sec=self.secs)

    @property
    def elapsed_time_hms(self):
        m, s = divmod(self.time, 60)
        h, m = divmod(m, 60)
        return (int(h), int(m), int(s))

    @property
    def hours(self):
        return self.elapsed_time_hms[0]

    @property
    def mins(self):
        return self.elapsed_time_hms[1]

    @property
    def secs(self):
        return self.elapsed_time_hms[2]

    @property
    def date(self):
        if self.is_multi_activity:
            return self.groupdate
        else:
            return self._date

    @property
    def is_plural(self):
        return len(self.activities) != 1

    @property
    def name(self):
        if self.is_multi_activity or self.groupdate:
            runs = "runs" if self.is_plural else "run"
            return "{} {}".format(len(self.activities), runs)
        else:
            try:
                return self._name
            except IndexError:
                return "No activity"

    @property
    def count(self):
        return len(self.activities)


def refresh_token(client):
    token = client.refresh_access_token(
        client_id=APP_ID, client_secret=SECRET, refresh_token=client.refresh_token
    )
    with open(CREDS, "w") as out:
        json.dump(token, out)

    return token


def load_token():
    with open(CREDS, "r") as f:
        token = json.load(f)
    return token


def current_month():
    return datetime.datetime.now()


def previous_month(curmonth=None):
    if curmonth is None:
        cur = current_month()
    else:
        cur = curmonth
    cur = cur.replace(day=1) - datetime.timedelta(days=1)
    return cur


def same_month(source, ref):
    return (source.month == ref.month) and (source.year == ref.year)


def same_year(source, ref):
    return source.year == ref.year


def pace(mtime, distance):
    secs = mtime.total_seconds()
    pace = secs / KM(distance).num
    m, s = divmod(pace, 60)
    return (int(m), int(s))


def get_activities(activities):
    data = ActivityHistory()
    act_sum = ActivitySummary
    cmonth = current_month()
    current = [a for a in activities if same_month(a.start_date_local, cmonth)]
    curacs = ActivitySummary.from_activities(current)
    curacs.groupdate = cmonth
    data.current = curacs

    month = cmonth
    for _ in range(SHOW_EXTRA_MONTHS):
        month = previous_month(month)
        previous = [a for a in activities if same_month(a.start_date_local, month)]
        summary = act_sum()
        summary.add_activities(previous)
        summary.groupdate = month
        data.add_month(summary)

    ysum = act_sum()
    yacts = [a for a in activities if same_year(a.start_date_local, cmonth)]
    ysum.add_activities(yacts)
    ysum.groupdate = cmonth
    data.year = ysum

    summary = act_sum()
    summary.add_activities(activities)
    summary.groupdate = month
    data.alltime = summary

    return data


def get_client():
    client = Client()
    token = load_token()
    client.refresh_token = token["refresh_token"]
    if token["expires_at"] < time.time():
        token = refresh_token(client)
    client.access_token = token["access_token"]
    return client


def update(interval=900):
    fetch = check_last_update(interval)

    if fetch:
        return fetch_data()

    else:
        return read_cache()


def check_last_update(interval):
    fetch = True
    now = time.time()

    if not os.path.isfile(TIMESTAMP):
        pass
    else:
        with open(TIMESTAMP, "r") as ts:
            stamp = ts.read().strip()

        try:
            last = float(stamp)
            if (now - last) < interval:
                fetch = False

        except ValueError:
            pass

    return fetch


def fetch_data():
    if not (APP_ID and SECRET):
        return (False, "Cannot read app_id and secret.")

    try:
        client = get_client()
    except Exception as e:
        return (False, e)

    acs = list(client.get_activities())
    data = get_activities(acs)

    cache_data(data)

    return (True, data)


def read_cache():
    try:
        with open(CACHE, "rb") as saved:
            data = pickle.load(saved)

        return (True, data)

    except pickle.PickleError as e:
        return (False, e)

    except FileNotFoundError:
        return (False, "Pickled data not found")


def cache_data(data):
    now = time.time()

    with open(TIMESTAMP, "w") as ts:
        ts.write(str(now))

    with open(CACHE, "wb") as pick:
        pickle.dump(data, pick)
