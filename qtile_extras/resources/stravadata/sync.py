import datetime
import json
import os
import pickle
import time
from units import unit

from stravalib import Client
from stravalib.model import Activity

from .locations import CREDS, RECORDS, AUTH, TIMESTAMP, CACHE

NUM_EVENTS = 5

APP_ID = AUTH.get("id", False)
SECRET = AUTH.get("secret", False)

SHOW_EXTRA_MONTHS = 5

KM = unit("km")


class ActivityHistory(object):

    def __init__(self):
        self.current = None
        self.previous = []
        self.year = None
        self.alltime = None

    def add_month(self, actsum):
        self.previous.append(actsum)


class ActivitySummary(object):
    def __init__(self,  distance_unit=unit("km"), groupdate=None, child=False):
        self.activities = []
        self.distance_unit = distance_unit
        self.dist = distance_unit(0)
        self.time = 0
        self._date = datetime.datetime.now()
        self.groupdate = groupdate
        self.paceformat = "{min:2.0f}:{sec:02.0f}"
        self.timeformat = "{hr:0d}:{min:02d}:{sec:02d}"
        self.child = child
        self.children = []
        self._name = ""

    @classmethod
    def fromActivity(cls, activity, distance_unit=unit("km"), child=False):
        act = cls(distance_unit=distance_unit, child=child)
        act.add_activity(activity)
        return act

    @classmethod
    def fromActivities(cls, activities, distance_unit=unit("km"), child=False):
        act = cls(distance_unit=distance_unit, child=child)
        act.add_activities(activities)
        return act

    def _isActivity(self, activity):
        return (type(activity) == Activity and activity.type == "Run")

    def createChild(self, activity):
        if not self.child:
            self.children.append(ActivitySummary.fromActivity(activity,
                                                              child=True))

    def add_activity(self, activity):
        if self._isActivity(activity):
            self.activities.append(activity)
            if not self.isMultiActivity:
                self._date = activity.start_date_local
                self._name = activity.name

            self.dist += activity.distance
            self.time += activity.moving_time.total_seconds()

            self.createChild(activity)

    def add_activities(self, activities):
        for act in activities:
            self.add_activity(act)

    @property
    def isMultiActivity(self):
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
        return self.dist.num

    @property
    def formatPace(self):
        min, sec = self.pace
        return self.paceformat.format(min=min, sec=sec)

    @property
    def formatTime(self):
        return self.timeformat.format(hr=self.hours,
                                      min=self.mins,
                                      sec=self.secs)

    @property
    def elapsedTimeHMS(self):
        m, s = divmod(self.time, 60)
        h, m = divmod(m, 60)
        return (int(h), int(m), int(s))

    @property
    def hours(self):
        return self.elapsedTimeHMS[0]

    @property
    def mins(self):
        return self.elapsedTimeHMS[1]

    @property
    def secs(self):
        return self.elapsedTimeHMS[2]

    @property
    def date(self):
        if self.isMultiActivity:
            return self.groupdate
        else:
            return self._date

    @property
    def isPlural(self):
        return len(self.activities) != 1

    @property
    def name(self):
        if self.isMultiActivity or self.groupdate:
            runs = "runs" if self.isPlural else "run"
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
    token = client.refresh_access_token(client_id=APP_ID,
                                        client_secret=SECRET,
                                        refresh_token=client.refresh_token)
    with open(CREDS, "w") as out:
        json.dump(token, out)

    return token


def load_token():
    with open(CREDS, "r") as f:
        token = json.load(f)
    return token


def load_records():
    if not os.path.isfile(RECORDS):
        return {"activities": [], "records": {}}

    with open(RECORDS, "r") as f:
        records = json.load(f)

    return records


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
    ActSum = ActivitySummary
    cmonth = current_month()
    current = [a for a in activities if same_month(a.start_date_local, cmonth)]
    curacs = ActivitySummary.fromActivities(current)
    curacs.groupdate = cmonth
    data.current = curacs

    month = cmonth
    for _ in range(SHOW_EXTRA_MONTHS):
        month = previous_month(month)
        previous = [a for a in activities
                    if same_month(a.start_date_local, month)]
        summary = ActSum()
        summary.add_activities(previous)
        summary.groupdate = month
        data.add_month(summary)

    ysum = ActSum()
    yacts = [a for a in activities if same_year(a.start_date_local, cmonth)]
    ysum.add_activities(yacts)
    ysum.groupdate = cmonth
    data.year = ysum

    summary = ActSum()
    summary.add_activities(activities)
    summary.groupdate = month
    data.alltime = summary

    return data


def update_records(acs, recs, client):
    for act in acs:
        if act.type != "Run":
            continue
        if act.id not in recs["activities"]:
            activity = client.get_activity(act.id)
            recs = add_record(activity, recs)
    return recs


def add_record(activity, recs):
    recs["activities"].append(activity.id)
    records = recs["records"]
    if activity.best_efforts is None:
        return recs

    for effort in activity.best_efforts:
        entry = {"time": effort.elapsed_time.total_seconds(),
                 "id": activity.id}
        if effort.name in records:
            records[effort.name].append(entry)
        else:
            records[effort.name] = [entry]

    return recs


def save_records(recs):
    with open(RECORDS, "w") as out:
        json.dump(recs, out)


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

    recs = load_records()
    recs = update_records(acs, recs, client)
    save_records(recs)

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
