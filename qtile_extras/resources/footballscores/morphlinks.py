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
class ML:
    MORPH_TEAMS_COMPS = (
        "/data/bbc-morph-football-teams-competitions-list/"
        "competitionURLTemplate/%2Fsport%2Ffootball"
        "%2F%7B%7Bslug%7D%7D%2Fscores-fixtures/"
        "teamURLTemplate/%2Fsport%2Ffootball%2Fteams"
        "%2F%7B%7Bslug%7D%7D%2Fscores-fixtures/version/3.1.0"
    )

    MORPH_FIXTURES_RESULTS = (
        "/data/bbc-morph-football-scores-"
        "match-list-data/endDate/{end_date}/startDate/"
        "{start_date}/{source}/version/2.2.3/"
        "withPlayerActions/{detailed}"
    )

    MORPH_FIXTURES_ALL = "tournament/full-priority-order"
