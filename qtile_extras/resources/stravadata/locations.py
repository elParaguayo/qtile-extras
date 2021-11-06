import json
import os

RECORDS_FILE = "records.json"
CREDS_FILE = "strava.json"
AUTH_FILE = "auth.json"
TIMESTAMP_FILE = "timestamp"
CACHE_FILE = "data.pickle"

STRAVA_DIR = os.path.join("~", ".cache", "stravawidget")
STRAVA_DIR = os.path.expanduser(STRAVA_DIR)

if not os.path.isdir(STRAVA_DIR):
    os.makedirs(STRAVA_DIR)

RECORDS = os.path.join(STRAVA_DIR, RECORDS_FILE)
CREDS = os.path.join(STRAVA_DIR, CREDS_FILE)
TIMESTAMP = os.path.join(STRAVA_DIR, TIMESTAMP_FILE)
AUTH_JSON = os.path.join(STRAVA_DIR, AUTH_FILE)
CACHE = os.path.join(STRAVA_DIR, CACHE_FILE)

try:
    with open(AUTH_JSON, "r") as authfile:
        AUTH = json.load(authfile)
except FileNotFoundError:
    AUTH = {}
