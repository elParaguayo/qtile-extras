import json
import time

from .locations import RECORDS

MILE = 1.60934

DISTANCES = {"400m": 0.4,
             "1/2 mile": MILE/2,
             "1k": 1,
             "1 mile": MILE,
             "2 mile": 2 * MILE,
             "5k": 5,
             "10k": 10,
             "15k": 15,
             "10 mile": 10 * MILE,
             "20k": 20,
             "Half-Marathon": 21.0975,
             "30k": 30}


def secs_to_hms(secs, pace=False):
    t = time.gmtime(secs)
    if pace:
        return time.strftime("%M:%S", t)
    return time.strftime("%H:%M:%S", t)


def show_all_records(recs=None):
    if recs is None:
        with open(RECORDS, "r") as f:
            recs = json.load(f)

    if not recs:
        return False

    best = {}

    for key in recs["records"]:
        fastest = sorted(recs["records"][key], key=lambda x: x["time"])
        sp = fastest[0]["time"]
        if key in DISTANCES:
            pace = secs_to_hms(sp / DISTANCES[key], True)
        else:
            pace = secs_to_hms(0, True)
        best[key] = (secs_to_hms(sp), pace)

    print("{:<14}{:>7}{:>12}{:>8}\n".format("Distance", "#", "Time", "Pace"))
    for key in best:
        print("{d:<14}{n:>6,}{0:>12}{1:>8}".format(*best[key],
                                                   d=key,
                                                   n=len(recs["records"][key])
                                                   ))


def show_records(recs=None, distance=None, limit=0):
    if recs is None:
        with open(RECORDS, "r") as f:
            recs = json.load(f)

    if not recs:
        return False

    results = sorted(recs["records"][distance], key=lambda x: x["time"])

    if limit > 0:
        results = results[:limit]

    if not results:
        print("No results found.")
        return

    print("Best results for {}:\n".format(distance))
    for n, result in enumerate(results):
        time = secs_to_hms(result["time"])
        pace = secs_to_hms(result["time"] / DISTANCES[distance], True)
        print("{}.\t{}\t{}".format(n+1, time, pace))
