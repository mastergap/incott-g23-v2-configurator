import os
import select
import time

DEV_PATH = '/dev/hidraw10'
# Our Sync Trigger: Report ID 09, Action 06, ID 09
TRIGGER = b'\x09\x06\x09\x00\x00\x00\x00\x00\x00'

def get_isolated_response():
    try:
        # 1. Open the device in Read/Write mode
        fd = os.open(DEV_PATH, os.O_RDWR | os.O_NONBLOCK)
        print(f"Connected to {DEV_PATH}")

        # 2. Flush the buffer: Read everything currently waiting
        print("Flushing heartbeat buffer...")
        while True:
            try:
                os.read(fd, 64)
            except OSError:
                break # Buffer is empty

        # 3. Send the Trigger
        print("Sending Trigger (06 09)...")
        os.write(fd, TRIGGER)

        # 4. Wait for the response (timeout after 500ms)
        print("Waiting for response...")
        r, _, _ = select.select([fd], [], [], 0.5)
        
        if r:
            data = os.read(fd, 64)
            print("\n--- ISOLATED RESPONSE ---")
            print(f"HEX: {data.hex(' ')}")
            print(f"RAW: {data}")
            print("-------------------------\n")
        else:
            print("No response received (Timeout).")

        os.close(fd)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_isolated_response()