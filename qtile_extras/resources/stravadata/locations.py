import json
from pathlib import Path

RECORDS_FILE = "records.json"
CREDS_FILE = "strava.json"
AUTH_FILE = "auth.json"
TIMESTAMP_FILE = "timestamp"
CACHE_FILE = "data.pickle"

CONFIG_DIR = Path("~/.config/stravawidget").expanduser()
CACHE_DIR = Path("~/.cache/stravawidget").expanduser()

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

AUTH_JSON = CONFIG_DIR / AUTH_FILE
CREDS = (CONFIG_DIR / CREDS_FILE).as_posix()
RECORDS = (CACHE_DIR / RECORDS_FILE).as_posix()
TIMESTAMP = (CACHE_DIR / TIMESTAMP_FILE).as_posix()
CACHE = (CACHE_DIR / CACHE_FILE).as_posix()

try:
    with AUTH_JSON.open() as authfile:
        AUTH = json.load(authfile)
except FileNotFoundError:
    AUTH = {}
