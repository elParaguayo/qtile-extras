# This Python file uses the following encoding: utf-8
"""This is a custom layout for the WordClock widget.

    Custom layouts can be created for the widget by creating a new file in the
    "qtile_extras.resources.wordclock" folder.

    Each layout must have the following variables:
        LAYOUT:   The grid layout. Must be a single string.
        MAP:      The mapping required for various times (see notes below)
        COLS:     The number of columns required for the grid layout
        ROWS:     The number of rows required for the grid layout
"""

# Thanks to: @crtvalentincic who contributed this layout to a previous project of mine

# Layout is a single string variable which will be looped over by the parser.
LAYOUT = (
    "HONIÄRCUBMWLRPI"
    "ENQKVARTRFDHALV"
    "ELTJUGOFEMEGTIO"
    "IOXÖVERIYTOLVVE"
    "ETTSEXTREEENIOE"
    "SJUENTVÅXELVAEN"
    "ÅTTATIOFYRAFEME"
    "RPIO'CLOCKHFMEM"
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
    "all": [0, 1, 2, 4, 5],
    "m00": [],
    "m05": [37, 38, 39, 48, 49, 50, 51],
    "m10": [42, 43, 44, 48, 49, 50, 51],
    "m15": [18, 19, 20, 21, 22, 48, 49, 50, 51],
    "m20": [32, 33, 34, 35, 36, 48, 49, 50, 51],
    "m25": [32, 33, 34, 35, 36, 37, 38, 39, 48, 49, 50, 51],
    "m30": [26, 27, 28, 29],
    "m35": [32, 33, 34, 35, 36, 37, 38, 39, 52],
    "m40": [32, 33, 34, 35, 36, 52],
    "m45": [18, 19, 20, 21, 22, 52],
    "m50": [42, 43, 44, 52],
    "m55": [37, 38, 39, 52],
    "h01": [60, 61, 62],
    "h02": [80, 81, 82],
    "h03": [66, 67, 68],
    "h04": [97, 98, 99, 100],
    "h05": [101, 102, 103],
    "h06": [63, 64, 65],
    "h07": [75, 76, 77],
    "h08": [90, 91, 92, 93],
    "h09": [71, 72, 73],
    "h10": [94, 95, 96],
    "h11": [84, 85, 86, 87],
    "h12": [54, 55, 56, 57],
    "am": [116, 117],
    "pm": [118, 119],
}

# Number of columns in grid layout
COLS = 15
ROWS = 8

# Is our language one where we need to increment the hour after 30 mins
# e.g. 9:40 is "Twenty to ten"
HOUR_INCREMENT = True

HOUR_INCREMENT_TIME = 29
