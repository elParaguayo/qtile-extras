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
    "ESÃORUMAPDUASNT"
    "TRESQUATROCINCO"
    "SEISGSETEVOITOM"
    "NOVEDEZONZEDOZE"
    "HORASOEÃMENOSLP"
    "UMXQUARTOSRPDEZ"
    "VINTEZEJCINCORX"
    "ETMEIAEMUPONTOP"
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
    "all": [60, 61, 62, 63],
    "m00": [111, 112, 114, 115, 116, 117, 118],
    "m05": [66, 98, 99, 100, 101, 102],
    "m10": [66, 87, 88, 89],
    "m15": [66, 75, 76, 78, 79, 80, 81, 82, 83],
    "m20": [66, 90, 91, 92, 93, 94],
    "m25": [66, 90, 91, 92, 93, 94, 96, 98, 99, 100, 101, 102],
    "m30": [66, 107, 108, 109, 110],
    "m35": [68, 69, 70, 71, 72, 90, 91, 92, 93, 94, 96, 98, 99, 100, 101, 102],
    "m40": [68, 69, 70, 71, 72, 90, 91, 92, 93, 94],
    "m45": [68, 69, 70, 71, 72, 75, 76, 78, 79, 80, 81, 82, 83],
    "m50": [68, 69, 70, 71, 72, 87, 88, 89],
    "m55": [68, 69, 70, 71, 72, 98, 99, 100, 101, 102],
    "h01": [0, 5, 6, 7],
    "h02": [1, 2, 3, 64, 9, 10, 11, 12],
    "h03": [1, 2, 3, 64, 15, 16, 17, 18],
    "h04": [1, 2, 3, 64, 19, 20, 21, 22, 23, 24],
    "h05": [1, 2, 3, 64, 25, 26, 27, 28, 29],
    "h06": [1, 2, 3, 64, 30, 31, 32, 33],
    "h07": [1, 2, 3, 64, 35, 36, 37, 38],
    "h08": [1, 2, 3, 64, 40, 41, 42, 43],
    "h09": [1, 2, 3, 64, 45, 46, 47, 48],
    "h10": [1, 2, 3, 64, 49, 50, 51],
    "h11": [1, 2, 3, 64, 52, 53, 54, 55],
    "h12": [1, 2, 3, 64, 56, 57, 58, 59],
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
