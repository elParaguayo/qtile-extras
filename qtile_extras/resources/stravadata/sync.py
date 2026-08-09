# Copyright (c) 2016-26 elParaguayo
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
from collections import defaultdict

from stravalib import Client, unit_helper
from stravalib.model import DetailedActivity, SummaryActivity

from qtile_extras.resources.stravadata.locations import AUTH, CACHE, CREDS, TIMESTAMP

NUM_EVENTS = 5

APP_ID = AUTH.get("id", False)
SECRET = AUTH.get("secret", False)

SHOW_EXTRA_MONTHS = 5

CYCLING_TYPES = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}
RUNNING_TYPES = {"Run", "TrailRun"}
WALKING_TYPES = {"Walk", "Hike"}


# --- Helper utilities ---


def _default_type_dict():
    return {"dist_km": 0.0, "time": 0, "count": 0}


def is_current_month(activity, now=None):
    now = now or datetime.datetime.now()
    d = getattr(activity, "start_date_local", None)
    if not d:
        return False
    return d.month == now.month and d.year == now.year


def is_current_year(activity, now=None):
    now = now or datetime.datetime.now()
    d = getattr(activity, "start_date_local", None)
    if not d:
        return False
    return d.year == now.year


def _get_sport_type_str(activity):
    """Extracts sport_type string safely from stravalib 2.5+ Pydantic models."""
    act_type = getattr(activity, "sport_type", None) or getattr(activity, "type", None)
    if act_type is None:
        return ""
    if hasattr(act_type, "value"):
        act_type = act_type.value
    elif hasattr(act_type, "root"):
        act_type = act_type.root
    return str(act_type).split(".")[-1]


def filter_activities(activities, sport_types=None, date_check=None):
    res = []
    for act in activities:
        act_type_str = _get_sport_type_str(act)

        if sport_types and act_type_str not in sport_types:
            continue
        if date_check and not date_check(act):
            continue
        res.append(act)
    return res


# --- Summary Data Models ---


class ActivityHistory:
    def __init__(self):
        self.current = None
        self.previous = []
        self.year = None
        self.alltime = None

    def add_month(self, actsum):
        self.previous.append(actsum)


class ActivitySummary:
    def __init__(self, activity_types=None, groupdate=None, child=False):
        self.activities = []
        self.activity_types = activity_types
        self.groupdate = groupdate
        self.child = child
        self.children = []
        self._date = datetime.datetime.now()
        self._name = ""

        self.by_type = defaultdict(_default_type_dict)

    @classmethod
    def from_activity(cls, activity, activity_types=None, child=False):
        act = cls(activity_types=activity_types, child=child)
        act.add_activity(activity)
        return act

    @classmethod
    def from_activities(cls, activities, activity_types=None, child=False):
        act = cls(activity_types=activity_types, child=child)
        act.add_activities(activities)
        return act

    def _is_activity(self, activity):
        if not isinstance(activity, SummaryActivity | DetailedActivity):
            return False

        act_type_str = _get_sport_type_str(activity)
        if not act_type_str:
            return False
        if self.activity_types is None:
            return True
        return act_type_str in self.activity_types

    def create_child(self, activity):
        if not self.child:
            self.children.append(
                ActivitySummary.from_activity(
                    activity, activity_types=self.activity_types, child=True
                )
            )

    def add_activity(self, activity):
        if not self._is_activity(activity):
            return

        act_type_str = _get_sport_type_str(activity)
        self.activities.append(activity)

        if not self.is_multi_activity:
            self._date = activity.start_date_local
            self._name = activity.name

        km_val = 0.0
        if activity.distance is not None:
            dist = unit_helper.kilometers(activity.distance)
            km_val = float(dist.magnitude if hasattr(dist, "magnitude") else dist)

        moving_secs = 0
        if activity.moving_time is not None:
            if isinstance(activity.moving_time, datetime.timedelta):
                moving_secs = int(activity.moving_time.total_seconds())
            elif hasattr(activity.moving_time, "magnitude"):
                moving_secs = int(activity.moving_time.magnitude)
            else:
                moving_secs = int(activity.moving_time)

        self.by_type[act_type_str]["dist_km"] += km_val
        self.by_type[act_type_str]["time"] += moving_secs
        self.by_type[act_type_str]["count"] += 1

        self.create_child(activity)

    def add_activities(self, activities):
        for act in activities:
            self.add_activity(act)

    def get_distance(self, act_types=None):
        if act_types:
            if isinstance(act_types, str):
                act_types = [act_types]
            return sum(self.by_type[t]["dist_km"] for t in act_types)
        return sum(v["dist_km"] for v in self.by_type.values())

    def get_count(self, act_types=None):
        if act_types:
            if isinstance(act_types, str):
                act_types = [act_types]
            return sum(self.by_type[t]["count"] for t in act_types)
        return sum(v["count"] for v in self.by_type.values())

    def get_time_seconds(self, act_types=None):
        if act_types:
            if isinstance(act_types, str):
                act_types = [act_types]
            return sum(self.by_type[t]["time"] for t in act_types)
        return sum(v["time"] for v in self.by_type.values())

    def get_format_time(self, act_types=None):
        secs = self.get_time_seconds(act_types)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{int(h)}:{int(m):02d}:{int(s):02d}"

    def get_speed(self, act_types=None):
        dist = self.get_distance(act_types)
        secs = self.get_time_seconds(act_types)
        return (dist / secs) * 3600 if secs > 0 else 0.0

    def get_pace(self, act_types=None):
        dist = self.get_distance(act_types)
        secs = self.get_time_seconds(act_types)
        if dist > 0:
            m, s = divmod(secs / dist, 60)
            return f"{int(m)}:{int(s):02d}"
        return "0:00"

    @property
    def distance(self):
        return self.get_distance()

    @property
    def count(self):
        return self.get_count()

    @property
    def format_time(self):
        return self.get_format_time()

    @property
    def format_pace(self):
        return self.get_pace()

    @property
    def is_multi_activity(self):
        return len(self.activities) > 1

    @property
    def date(self):
        return self.groupdate if self.is_multi_activity else self._date

    @property
    def is_plural(self):
        return len(self.activities) != 1

    @property
    def name(self):
        if self.is_multi_activity or self.groupdate:
            return f"{len(self.activities)} activities" if self.is_plural else "1 activity"
        return self._name or "No activity"


# --- OAuth & API Sync ---
def refresh_token(client, current_refresh_token):
    # Ensure client_id is formatted correctly as int or numeric str
    cid = int(APP_ID) if APP_ID else None
    sec = str(SECRET) if SECRET else None

    client.client_id = cid
    client.client_secret = sec

    token = client.refresh_access_token(
        client_id=cid,
        client_secret=sec,
        refresh_token=current_refresh_token,
    )
    with open(CREDS, "w") as out:
        json.dump(token, out)
    return token


def get_client():
    client = Client()
    cid = int(APP_ID) if APP_ID else None
    sec = str(SECRET) if SECRET else None

    client.client_id = cid
    client.client_secret = sec

    token = load_token()

    # Check if token is expired (or missing expires_at)
    if token.get("expires_at", 0) < time.time():
        token = refresh_token(client, token["refresh_token"])

    client.access_token = token["access_token"]
    client.refresh_token = token["refresh_token"]
    return client


def load_token():
    with open(CREDS) as f:
        token = json.load(f)
    return token


def current_month():
    return datetime.datetime.now()


def previous_month(curmonth=None):
    cur = curmonth or current_month()
    return cur.replace(day=1) - datetime.timedelta(days=1)


def same_month(source, ref):
    if not source:
        return False
    return (source.month == ref.month) and (source.year == ref.year)


def same_year(source, ref):
    if not source:
        return False
    return source.year == ref.year


def get_activities(activities, activity_types=None):
    data = ActivityHistory()
    cmonth = current_month()

    current = [a for a in activities if same_month(getattr(a, "start_date_local", None), cmonth)]
    curacs = ActivitySummary.from_activities(current, activity_types=activity_types)
    curacs.groupdate = cmonth
    data.current = curacs

    month = cmonth
    for _ in range(SHOW_EXTRA_MONTHS):
        month = previous_month(month)
        previous = [
            a for a in activities if same_month(getattr(a, "start_date_local", None), month)
        ]
        summary = ActivitySummary(activity_types=activity_types)
        summary.add_activities(previous)
        summary.groupdate = month
        data.add_month(summary)

    ysum = ActivitySummary(activity_types=activity_types)
    yacts = [a for a in activities if same_year(getattr(a, "start_date_local", None), cmonth)]
    ysum.add_activities(yacts)
    ysum.groupdate = cmonth
    data.year = ysum

    all_sum = ActivitySummary(activity_types=activity_types)
    all_sum.add_activities(activities)
    all_sum.groupdate = month
    data.alltime = all_sum

    return data


# def get_client():
#     client = Client()
#     token = load_token()

#     if token.get("expires_at", 0) < time.time():
#         token = refresh_token(client, token["refresh_token"])

#     client.access_token = token["access_token"]
#     client.refresh_token = token["refresh_token"]
#     return client


def get_strava_data(interval=1800, activity_types=None):
    fetch = check_last_update(interval)
    if fetch:
        return fetch_data(activity_types=activity_types)
    return read_cache()


def check_last_update(interval):
    if not os.path.isfile(TIMESTAMP):
        return True

    with open(TIMESTAMP) as ts:
        stamp = ts.read().strip()

    try:
        return (time.time() - float(stamp)) >= interval
    except ValueError:
        return True


def fetch_data(activity_types=None):
    if not (APP_ID and SECRET):
        return (False, "Cannot read app_id and secret.")

    try:
        client = get_client()
        raw_activities = list(client.get_activities(limit=None))
        history_data = get_activities(raw_activities, activity_types=activity_types)
        payload = {"history": history_data, "raw": raw_activities}
        cache_data(payload)
        return (True, payload)
    except Exception as e:
        return (False, e)


def read_cache():
    try:
        with open(CACHE, "rb") as saved:
            payload = pickle.load(saved)
        return (True, payload)
    except pickle.PickleError as e:
        return (False, e)
    except FileNotFoundError:
        return (False, "Pickled data not found")


def cache_data(payload):
    now = time.time()
    with open(TIMESTAMP, "w") as ts:
        ts.write(str(now))
    with open(CACHE, "wb") as pick:
        pickle.dump(payload, pick)
