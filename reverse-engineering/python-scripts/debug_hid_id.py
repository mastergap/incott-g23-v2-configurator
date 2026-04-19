#!/usr/bin/env python3
import glob
import os

for path in glob.glob("/sys/class/hidraw/hidraw10/device"):
    try:
        uevent_path = os.path.join(path, "uevent")
        with open(uevent_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                print(repr(line))
                if 'HID_ID=' in line:
                    print("Found HID_ID line!")
                    parts = line.split('=')
                    print(f"  Parts after split: {parts}")
                    if len(parts) > 1:
                        hid_val = parts[1].strip()
                        print(f"  HID value: {hid_val}")
                        vid_pid = hid_val.split(':')
                        print(f"  VID:PID split: {vid_pid}")
                        if len(vid_pid) >= 2:
                            vid = int(vid_pid[0], 16)
                            pid = int(vid_pid[1], 16)
                            print(f"  VID: 0x{vid:04x}, PID: 0x{pid:04x}")
    except Exception as e:
        print(f"Error: {e}")
