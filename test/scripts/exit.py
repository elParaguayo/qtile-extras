# Minimal script used for test_scriptexit.py
import sys

# We want this to raise an error if it gets an invalid number of args
if not len(sys.argv) == 2:
    sys.exit(1)


# Otherwise write some text to a file
with open(sys.argv[1], "w") as f:
    f.write("CLOSED")
