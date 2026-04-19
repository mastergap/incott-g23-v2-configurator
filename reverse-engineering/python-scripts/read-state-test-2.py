import hid
import time
import sys

# Constants
VID = 0x093a
PIDS = {0x622c: "⚡ Wired", 0x522c: "📶 Wireless"}

def brute_force_open():
    all_devices = hid.enumerate()
    # Filter for our Vendor ID
    targets = [d for d in all_devices if d['vendor_id'] == VID]
    
    if not targets:
        print("❌ No Incott devices found. Check USB connection.")
        return None, None

    print(f"🔍 Found {len(targets)} interfaces. Searching for the Config Gate...")

    # Debug: print all targets
    for i, dev in enumerate(targets):
        print(f"  Interface {i}: path={dev['path']}, interface_number={dev['interface_number']}, usage_page={dev.get('usage_page')}, usage={dev.get('usage')}")

    # We prioritize Interface 1 or 2, as 0 is always the mouse cursor (busy)
    for dev_info in sorted(targets, key=lambda x: x['interface_number'], reverse=True):
        path = dev_info['path']
        iface = dev_info['interface_number']
        pid = dev_info['product_id']
        mode = PIDS.get(pid, "❓ Unknown")

        print(f"Trying interface {iface} (path: {path})")
        h = hid.device()
        try:
            h.open_path(path)
            h.set_nonblocking(True)
            
            # Send a Sync Request to see if this interface talks back
            # 9-byte feature report: [ReportID, Cmd, SubCmd, ...]
            h.send_feature_report([0x09, 0x06, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            
            # Wait and check for response
            for _ in range(15): 
                res = h.read(64)
                if res and res[0] == 0x09:
                    print(f"✅ Success! Connected to {mode} (Interface {iface})")
                    return h, mode
                time.sleep(0.02)
            
            h.close()
            print(f"No response from interface {iface}")
        except Exception as e:
            print(f"Exception on interface {iface}: {e}")
            continue
            
    return None, None

def run_monitor(h, mode):
    print("--- Starting Live Display ---")
    last_sync = 0
    try:
        while True:
            # Request update every 2 seconds
            if time.time() - last_sync > 2:
                h.send_feature_report([0x09, 0x06, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                last_sync = time.time()

            data = h.read(64)
            if data and data[0] == 0x09:
                # Optimized Parser for G23V2SE
                bat = data[1]
                slot = (data[2] >> 4) + 1
                poll = {0:1000, 1:500, 2:250, 3:125}.get(data[2] & 0x0F, "???")
                
                # DPI Logic: data[4] high/low nibbles are multipliers
                mx = 5 if (data[4] & 0x0F) > 0 else 1
                my = 5 if (data[4] >> 4) > 0 else 1
                dx, dy = (data[5]+1)*50*mx, (data[6]+1)*50*my
                
                # Clean live line
                output = f"\r[{mode}] 🔋 {bat}% | DPI: {dx}x{dy} | {poll}Hz | Profile: {slot}    "
                sys.stdout.write(output)
                sys.stdout.flush()
                
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped.")
    finally:
        h.close()

if __name__ == "__main__":
    device, mode_label = brute_force_open()
    if device:
        run_monitor(device, mode_label)
    else:
        print("\n🛑 CONFIG INTERFACE LOCKED OR SILENT.")
        print("Try this: Unplug the dongle, wait 3 seconds, plug it back in,")
        print("run 'sudo chmod 666 /dev/hidraw*' and try the script again.")