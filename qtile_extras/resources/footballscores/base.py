import json
import time

import requests

from qtile_extras.resources.footballscores.exceptions import FSConnectionError

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

from qtile_extras.resources.footballscores.morphlinks import ML

API_BASE = "http://push.api.bbci.co.uk/p"
API_MORPH = "morph:/"
REFERER = "http://www.bbc.co.uk/sport/football/scores-fixtures"


class FSBase(object):
    '''class for common functions for match classes.'''

    LAST_REQUEST = 0
    REQUEST_COUNT = 1

    def __init__(self, retry_count=5, timeout=0.5):
        self.RETRY_COUNT = retry_count
        self.TIMEOUT = 0.5

    def __create_payload(self, page):

        now = time.time()
        if now - type(self).LAST_REQUEST < 30:
            type(self).REQUEST_COUNT += 1
        else:
            type(self).REQUEST_COUNT = 1

        page = API_MORPH + page

        type(self).LAST_REQUEST = now

        return {"t": page, "c": type(self).REQUEST_COUNT}

    def check_page(self, page):

        try:
            rq = requests.head(page)
            return rq.status_code == 200
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            return False

    def send_request(self, page):

        payload = self.__create_payload(page)

        for _ in range(self.RETRY_COUNT):
            try:
                result = requests.get(API_BASE, params=payload,
                                      headers={"Referer": REFERER}).json()
                if result["moments"]:
                    return result["moments"]
            except JSONDecodeError:
                pass
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout):
                raise FSConnectionError

            time.sleep(self.TIMEOUT)

        return None

    # Unused?
    def request_push_stream(self, page):

        payload = self.__create_payload(page)

        r = requests.get(API_BASE, params=payload,
                         headers={"Referer": REFERER}, stream=True).json()

        return r

    def get_teams(self):

        teams = self.send_request(ML.MORPH_TEAMS_COMPS)

        if teams:
            teams = json.loads(teams[0]["payload"])
            return [x for x in teams if "teams" in x["url"]]

    def get_tournaments(self):

        teams = self.send_request(ML.MORPH_TEAMS_COMPS)

        if teams:
            teams = json.loads(teams[0]["payload"])
            return [x for x in teams if "teams" not in x["url"]]


def get_all_teams():
    return FSBase().get_teams()


def get_all_tournaments():
    return FSBase().get_tournaments()
