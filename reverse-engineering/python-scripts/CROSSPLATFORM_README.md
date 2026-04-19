# Cross-Platform Incott G23V2SE Mouse Configuration

This solution provides cross-platform HID access for the Incott Esports G23V2SE mouse.

## Platform Support

- **Linux**: Uses native `hidraw` with `fcntl` ioctl (most reliable)
- **Windows/macOS**: Uses `hidapi` library (via PyHIDAPI)

## Installation

### Linux

No additional dependencies needed. Just ensure you have the correct udev rules for the mouse:

```bash
# Add this to /etc/udev/rules.d/99-incott-mouse.rules
KERNEL=="hidraw*", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="093a", MODE="0666", TAG+="uaccess"

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Windows/macOS

Install hidapi:

```bash
pip install hidapi
```

## Usage

### Monitor Current Settings

```bash
python3 mouse_monitor_crossplatform.py
```

Output:
```
🖱️  Incott G23V2SE Cross-Platform Monitor
Platform: linux
✅ Found device: /dev/hidraw10
🔌 Connected. Requesting state...
[⚡ Wired] | Bat: 100% | Slot: 1 | DPI: 400x400 | Poll: 1000Hz | Debounce: 8ms
```

### Programmatic Access

```python
from mouse_hid import create_mouse_hid

# Create HID handler (platform-aware)
hid = create_mouse_hid(0x093a, [0x622c, 0x522c])

# Find device
device_path = hid.find_device()
if not device_path:
    print("Device not found")
    exit(1)

# Open device
hid.open(device_path)

# Send feature report
hid.send_feature_report([0x09, 0x06, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

# Read response
data = hid.read(64)
if data and data[0] == 0x09:
    print("Received heartbeat:", data.hex())

# Close
hid.close()
```

## Protocol Reference

### Sync Request (PC → Mouse)
```
Byte 0: 0x09    (Report ID)
Byte 1: 0x06    (Command: Heartbeat)
Byte 2: 0x09    (Sub-command)
Bytes 3-8: 0x00 (Padding)
```

### Heartbeat Response (Mouse → PC)
```
Byte 0: 0x09         (Report ID)
Byte 1: Battery %    (0-100)
Byte 2: Slot & Poll  (High nibble: active slot, Low nibble: polling rate)
Byte 3: Debounce ms
Byte 4: DPI Mults    (High nibble: Y, Low nibble: X)
Byte 5: DPI X (LSB)
Byte 6: DPI Y (MSB)
Byte 7: Sensor flags
Bytes 8-31: Reserved
```

## Troubleshooting

### Linux: "Access Denied"
Ensure udev rules are installed and reload them:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Or temporarily grant permissions:
```bash
sudo chmod 666 /dev/hidraw*
```

### Windows/macOS: "Device not found"
Ensure hidapi is installed and the mouse is connected:
```bash
pip install hidapi
```

### hidapi fails on Linux
The `mouse_hid.py` fallback to hidapi may fail if libusb backend is used instead of hidraw. The native hidraw implementation (`mouse_monitor_crossplatform.py`) is preferred on Linux.

## Architecture

```
mouse_hid.py (Abstraction Layer)
├── LinuxMouseHID      (hidraw + fcntl - Linux only)
└── HIDAPIMouseHID     (PyHIDAPI - Windows/macOS/Linux fallback)

mouse_monitor_crossplatform.py (Client)
└── Uses platform-appropriate implementation via factory
```

## Files

- `mouse_hid.py` - Platform abstraction layer
- `mouse_monitor_crossplatform.py` - Cross-platform monitor utility
- `read-state-test.py` - Original Linux-only implementation (reference)
- `read-state-test-2.py` - Original hidapi implementation (reference)
