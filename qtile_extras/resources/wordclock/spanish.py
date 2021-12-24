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
    "ESONPLASWUNADOS"
    "TRESCUATROCINCO"
    "SEISIETEOCHONCE"
    "NUEVESDIEZVDOCE"
    "YMENOSQCINCORPI"
    "DIEZTRCUARTOELP"
    "VEINTEBMEDIALZI"
    "QTIVEINTICINCOR"
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
    "all": [],
    "m00": [],
    "m05": [60, 67, 68, 69, 70, 71],
    "m10": [60, 75, 76, 77, 78],
    "m15": [60, 81, 82, 83, 84, 85, 86],
    "m20": [60, 90, 91, 92, 93, 94, 95],
    "m25": [60, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118],
    "m30": [60, 97, 98, 99, 100, 101],
    "m35": [61, 62, 63, 64, 65, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118],
    "m40": [61, 62, 63, 64, 65, 90, 91, 92, 93, 94, 95],
    "m45": [61, 62, 63, 64, 65, 81, 82, 83, 84, 85, 86],
    "m50": [61, 62, 63, 64, 65, 75, 76, 77, 78],
    "m55": [61, 62, 63, 64, 65, 67, 68, 69, 70, 71],
    "h01": [0, 1, 5, 6, 9, 10, 11],
    "h02": [1, 2, 3, 5, 6, 7, 12, 13, 14],
    "h03": [1, 2, 3, 5, 6, 7, 15, 16, 17, 18],
    "h04": [1, 2, 3, 5, 6, 7, 19, 20, 21, 22, 23, 24],
    "h05": [1, 2, 3, 5, 6, 7, 25, 26, 27, 28, 29],
    "h06": [1, 2, 3, 5, 6, 7, 30, 31, 32, 33],
    "h07": [1, 2, 3, 5, 6, 7, 33, 34, 35, 36, 37],
    "h08": [1, 2, 3, 5, 6, 7, 38, 39, 40, 41],
    "h09": [1, 2, 3, 5, 6, 7, 45, 46, 47, 48, 49],
    "h10": [1, 2, 3, 5, 6, 7, 51, 52, 53, 54],
    "h11": [1, 2, 3, 5, 6, 7, 41, 42, 43, 44],
    "h12": [1, 2, 3, 5, 6, 7, 56, 57, 58, 59],
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
