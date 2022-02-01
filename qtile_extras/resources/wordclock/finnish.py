# This Python file uses the following encoding: utf-8
"""This is a custom layout for the WordClock widget.

    Custom layouts can be created for the widget by creating a new file in the
    "qtile_extras.resources.wordclock" folder.

    Each layout must have the follo
    wing variables:
        LAYOUT:   The grid layout. Must be a single string.
        MAP:      The mapping required for various times (see notes below)
        COLS:     The number of columns required for the grid layout
        ROWS:     The number of rows required for the grid layout
"""

# Thanks to: @karrika who contributed this layout to a previous project of mine

# Layout is a single string variable which will be looped over by the parser.
LAYOUT = (
    "KELLOQONYPUOLIWPWKL"  # 0
    "AKYMMENTÄXVARTTIAZC"  # 19
    "KAHTAKYMMENTÄVIITTÄ"  # 38
    "VAILLEYLIBSEITSEMÄN"  # 57
    "YKSITOISTAKAHDEKSAN"  # 76
    "KAKSITOISTAYHDEKSÄN"  # 95
    "KYMMENENTKOLMENELJÄ"  # 114
    "KUUSIVIISIIIVAAPIIP"
)  # 133

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
    "all": [0, 1, 2, 3, 4, 6, 7],
    "m00": [],
    "m05": [51, 52, 53, 54, 55, 56, 63, 64, 65],
    "m10": [20, 21, 22, 23, 24, 25, 26, 27, 63, 64, 65],
    "m15": [29, 30, 31, 32, 33, 34, 35, 63, 64, 65],
    "m20": [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 63, 64, 65],
    "m25": [
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46,
        47,
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        63,
        64,
        65,
    ],
    "m30": [9, 10, 11, 12, 13],
    "m35": [
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46,
        47,
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        59,
        60,
        61,
        62,
    ],
    "m40": [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 57, 58, 59, 60, 61, 62],
    "m45": [29, 30, 31, 32, 33, 34, 35, 57, 58, 59, 60, 61, 62],
    "m50": [20, 21, 22, 23, 24, 25, 26, 27, 57, 58, 59, 60, 61, 62],
    "m55": [51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62],
    "h01": [76, 77, 78, 79],
    "h02": [95, 96, 97, 98, 99],
    "h03": [123, 124, 125, 126, 127],
    "h04": [128, 129, 130, 131, 132],
    "h05": [138, 139, 140, 141, 142],
    "h06": [133, 134, 135, 136, 137],
    "h07": [67, 68, 69, 70, 71, 72, 73, 74, 75],
    "h08": [86, 87, 88, 89, 90, 91, 92, 93, 94],
    "h09": [106, 107, 108, 109, 110, 111, 112, 113],
    "h10": [114, 115, 116, 117, 118, 119, 120, 121],
    "h11": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85],
    "h12": [95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105],
    "am": [147, 148],
    "pm": [150, 151],
}

# Number of columns in grid layout
COLS = 19
ROWS = 8

# Is our language one where we need to increment the hour after 30 mins
# e.g. 9:40 is "Twenty to ten"
HOUR_INCREMENT = True

HOUR_INCREMENT_TIME = 29
