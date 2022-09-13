import sys
import time

for x in range(1, 6):
    sys.stdout.write(f"Line: {x}\n")
    sys.stdout.flush()
    time.sleep(1)
