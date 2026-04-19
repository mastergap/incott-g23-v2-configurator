#!/usr/bin/env python3
import glob
import os

VID = "093a"
for path in glob.glob("/sys/class/hidraw/hidraw*/device"):
    try:
        uevent_path = os.path.join(path, "uevent")
        with open(uevent_path, "r") as f:
            content = f.read()
            print(f"File: {uevent_path}")
            print("Content:")
            print(content)
            print("=" * 50)
    except Exception as e:
        print(f"Error reading {path}: {e}")
