# -*- coding: utf-8 -*-
"""This is a custom layout for the WordClock widget.

    Custom layouts can be created for the widget by creating a new file in the
    "qtile_extras.resources.wordclock" folder.

    Each layout must have the following variables:
        LAYOUT:   The grid layout. Must be a single string.
        MAP:      The mapping required for various times (see notes below)
        COLS:     The number of columns required for the grid layout
        ROWS:     The number of rows required for the grid layout
"""

# Layout is a single string variable which will be looped over by the parser.
LAYOUT = (
    "ILNESTHUNEDEUXP"
    "TROISIXOQUATREM"
    "CINQHUITNEUFDIX"
    "ONZEBDOUZERSEPT"
    "HEURESRASPBERRY"
    "ETMOINSUCINQDIX"
    "LEJQUARTFDEMIEL"
    "QTIVINGT-CINQKU"
)

# Map instructions:
# The clock works by rounding the time to the nearest 5 minutes.
# This means that you need to have settngs for each five minute interval "m00"
# "m00", "m05".
# The clock also works on a 12 hour basis rather than 24 hour:
# "h00", "h01" etc.
# There are three optional parameters:
#   "all": Anything that is always shown regardless of the time e.g. "It is..."
#   "am":  Wording/symbol to indicate morning.
#   "pm":  Wording/symbol to indicate afternoon/evening
MAP = {
    "all": [0, 1, 3, 4, 5, 60, 61, 62, 63, 64],
    "m00": [],
    "m05": [83, 84, 85, 86],
    "m10": [87, 88, 89],
    "m15": [75, 76, 93, 94, 95, 96, 97],
    "m20": [108, 109, 110, 111, 112],
    "m25": [108, 109, 110, 111, 112, 113, 114, 115, 116, 117],
    "m30": [75, 76, 99, 100, 101, 102, 103],
    "m35": [77, 78, 79, 80, 81, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117],
    "m40": [77, 78, 79, 80, 81, 108, 109, 110, 111, 112],
    "m45": [77, 78, 79, 80, 81, 90, 91, 93, 94, 95, 96, 97],
    "m50": [77, 78, 79, 80, 81, 87, 88, 89],
    "m55": [77, 78, 79, 80, 81, 83, 84, 85, 86],
    "h01": [7, 8, 9],
    "h02": [65, 10, 11, 12, 13],
    "h03": [65, 15, 16, 17, 18],
    "h04": [65, 23, 24, 25, 26, 27, 28],
    "h05": [65, 30, 31, 32, 33],
    "h06": [65, 19, 20, 21],
    "h07": [65, 56, 57, 58, 59],
    "h08": [65, 34, 35, 36, 37],
    "h09": [65, 38, 39, 40, 41],
    "h10": [65, 42, 43, 44],
    "h11": [65, 45, 46, 47, 48],
    "h12": [65, 50, 51, 52, 53, 54],
    "am": [],
    "pm": [],
}

# Number of columns in grid layout
COLS = 15
ROWS = 8

# Is our language one where we need to increment the hour after 30 mins
# e.g. 9:40 is "Twenty to ten"
HOUR_INCREMENT = True

HOUR_INCREMENT_TIME = 30
