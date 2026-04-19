"""
Cross-platform Incott G23V2SE mouse state reader.
Works on Linux (hidraw), Windows/macOS (hidapi).
"""

import sys
import time
from mouse_hid import create_mouse_hid

# Incott hardware constants
VID = 0x093a
PIDS = {0x622c: "⚡ Wired", 0x522c: "📶 Wireless"}
SYNC_REQUEST = bytes([0x09, 0x06, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def parse_heartbeat(data, mode):
    """Parse the 32-byte heartbeat response."""
    if len(data) < 8:
        return None
    
    battery = data[1]
    slot = (data[2] >> 4) + 1
    poll_map = {0: 1000, 1: 500, 2: 250, 3: 125}
    polling = poll_map.get(data[2] & 0x0F, "???")
    debounce = data[3]
    
    # DPI calculation: data[4] contains multipliers
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
    }


def format_status(status):
    """Format parsed status for display."""
    if not status:
        return None
    return (
        f"[{status['mode']}] | Bat: {status['battery']}% | "
        f"Slot: {status['slot']} | DPI: {status['dpi_x']}x{status['dpi_y']} | "
        f"Poll: {status['polling_hz']}Hz | Debounce: {status['debounce_ms']}ms"
    )


def main():
    """Main entry point."""
    print("🖱️  Incott G23V2SE Cross-Platform Monitor")
    print(f"Platform: {sys.platform}")
    
    # Create platform-appropriate HID handler
    try:
        hid = create_mouse_hid(VID, list(PIDS.keys()))
    except ImportError as e:
        print(f"❌ {e}")
        return 1
    
    # Find device
    result = hid.find_device()
    if result is None or result == (None, None):
        print("❌ Mouse not found. Check USB connection.")
        return 1
    
    device_path, product_id = result
    
    # Determine connection mode
    mode = PIDS.get(product_id, "❓ Unknown")
    print(f"✅ Found device: {device_path} ({mode}, PID: 0x{product_id:04x})")
    
    # Open device
    try:
        hid.open(device_path)
        print(f"🔌 Connected. Requesting state...")
    except Exception as e:
        print(f"❌ Failed to open device: {e}")
        return 1
    
    # Main loop
    try:
        # Send initial sync request
        hid.send_feature_report(SYNC_REQUEST)
        
        last_update = time.time()
        while True:
            # Periodic sync request
            if time.time() - last_update > 2:
                hid.send_feature_report(SYNC_REQUEST)
                last_update = time.time()
            
            # Read response
            packet = hid.read(64)
            if packet and len(packet) > 0 and packet[0] == 0x09:
                status = parse_heartbeat(packet, mode)
                
                if status:
                    formatted = format_status(status)
                    sys.stdout.write(f"\r{formatted}    ")
                    sys.stdout.flush()
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        hid.close()


if __name__ == "__main__":
    sys.exit(main())
