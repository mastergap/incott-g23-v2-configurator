import os
import sys
import glob
import time
import select
import fcntl
import struct

# Hardware Identity from your lsusb
VID = "093a"
PIDS = {"622c": "⚡ Wired", "522c": "📶 Wireless"}
# HID feature reports are 9 bytes long for writes.
TRIGGER = b"\x09\x06\x09\x00\x00\x00\x00\x00\x00"

# ioctl constants for HID
def HIDIOCSFEATURE(length):
    return 0xC0004806 | (length << 16)

def find_mouse_path():
    """Finds the hidraw node by looking at the parent directory name."""
    candidates = []
    for path in glob.glob("/sys/class/hidraw/hidraw*/device"):
        try:
            with open(os.path.join(path, "uevent"), "r") as f:
                content = f.read().lower()
                if VID in content:
                    node_name = path.split('/')[-2]
                    mode = "📶 Wireless"
                    for pid_code, label in PIDS.items():
                        if pid_code in content:
                            mode = label
                            break
                    candidates.append((f"/dev/{node_name}", mode))
        except Exception:
            continue
    if candidates:
        print(f"Found candidates: {candidates}")
        return candidates[-1]  # Return the last one (highest interface)
    return None, None

def parse_heartbeat(data, mode):
    if len(data) < 8: return None
    
    battery = data[1]
    slot = (data[2] >> 4) + 1
    poll_map = {0: 1000, 1: 500, 2: 250, 3: 125}
    polling = poll_map.get(data[2] & 0x0F, "???")
    debounce = data[3]
    
    # DPI Multiplier: Low Nibble = X, High Nibble = Y
    mult_x = 5 if (data[4] & 0x0F) > 0 else 1
    mult_y = 5 if (data[4] >> 4) > 0 else 1
    dpi_x = (data[5] + 1) * 50 * mult_x
    dpi_y = (data[6] + 1) * 50 * mult_y

    return {
        "mode": mode,
        "battery": battery,
        "slot": slot,
        "dpi_x": dpi_x,
        "dpi_y": dpi_y,
        "polling_hz": polling,
        "debounce_ms": debounce,
        "raw_bytes": data,
    }


def format_status(status):
    if not status:
        return None
    return (
        f"[{status['mode']}] | Bat: {status['battery']}% | Slot: {status['slot']} | "
        f"X: {status['dpi_x']} | Y: {status['dpi_y']} | "
        f"Poll: {status['polling_hz']}Hz | Deb: {status['debounce_ms']}ms"
    )


def send_sync(fd):
    try:
        # Send feature report using ioctl
        fcntl.ioctl(fd, HIDIOCSFEATURE(len(TRIGGER)), TRIGGER)
        print(f"🔁 Sent sync request: {TRIGGER.hex(' ')}")
    except OSError as e:
        print(f"⚠️ Could not send sync request: {e}")


def main():
    node, mode = find_mouse_path()
    
    if not node:
        print("❌ Still can't find it. Let's do a manual check.")
        print("Please run: ls -l /sys/class/hidraw/hidraw*/device")
        return

    print(f"✅ Found {mode} on {node}")
    
    try:
        # Open in Non-Blocking
        fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
        print(f"🔌 Connected to {node}. Starting heartbeat monitor...")

        send_sync(fd)

        send_sync(fd)

        while True:
            try:
                packet = os.read(fd, 64)
                if packet:
                    print(f"DEBUG: Read Packet: {packet.hex(' ')}")
                    if packet[0] == 0x09:
                        status = parse_heartbeat(packet, mode)
                        if status:
                            human = format_status(status)
                            print("\n--- HEARTBEAT ---")
                            print(human)
                            sys.stdout.write(f"\r{human}    ")
                            sys.stdout.flush()
            except BlockingIOError:
                pass
            
            time.sleep(0.1)

    except PermissionError:
        print(f"\n🚫 Access Denied to {node}. Try: sudo chmod 666 {node}")
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
    finally:
        if 'fd' in locals():
            os.close(fd)

if __name__ == "__main__":
    main()