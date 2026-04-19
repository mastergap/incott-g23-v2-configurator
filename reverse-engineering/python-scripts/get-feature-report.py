import os
import time

DEV_PATH = '/dev/hidraw10'

def probe_sync_commands():
    fd = os.open(DEV_PATH, os.O_RDWR)
    # Common "Read All" commands for Incott/Pixart
    commands = [
        b'\x09\x01\x01\x00\x00\x00\x00\x00\x00', # Request Profile
        b'\x09\x02\x01\x00\x00\x00\x00\x00\x00', # Request DPI Table
        b'\x09\x03\x01\x00\x00\x00\x00\x00\x00', # Request Buttons
        b'\x09\x05\x01\x00\x00\x00\x00\x00\x00', # Request Advanced (LOD/Debounce)
        b'\x09\x06\x01\x00\x00\x00\x00\x00\x00', # Request Memory Bank 1
    ]

    for cmd in commands:
        print(f"Testing Command: {cmd.hex(' ')}")
        os.write(fd, cmd)
        time.sleep(0.1)
        # We don't read here, let your 'cat' terminal show the results
    
    os.close(fd)

probe_sync_commands()