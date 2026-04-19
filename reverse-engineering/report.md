# Incott G23V2SE HID Protocol Specification

**Target Hardware:** Incott Esports G23V2SE (Pixart 3395)
**USB ID:** `093a:622c`
**Interface:** Linux `/dev/hidraw` (Management Node)

## 0. Connectivity Detection
The software distinguishes between connection modes via the USB Product ID (PID):

| Mode | Product ID (Hex) | Product ID (Dec) |
| :--- | :--- | :--- |
| **Wired** | `622c` | `25132` |
| **Wireless** | `522c` | `21036` |

**Detection Logic:** Applications should filter for Vendor ID `093a` and then check the PID to toggle UI elements (e.g., hiding battery status when wired, or showing a signal strength icon when wireless). The interface that sends the hearthbeat messages is the one with the higher number (usually 2).

## 1. The Inbound Heartbeat (Status Report)
The mouse broadcasts a 32-byte status message whenever its state changes or a sync is requested. This allows a TUI to reflect the physical state of the hardware in real-time.

**Report ID:** `09`  
**Payload Length:** 32 Bytes  
**Trigger:** The mouse is sending a report by himself. OLD behavior: Sent by hardware on DPI button press, physical connection change, or via `09 06 09` sync request.

### 1.1 Byte-by-Byte Memory Map

| Offset | Name | Type | Description |
| :--- | :--- | :--- | :--- |
| **0** | `Report ID` | `uint8` | Always `09`. |
| **1** | `Battery` | `uint8` | Battery percentage (0-100 decimal). |
| **2** | `Slot & Poll` | `bitfield` | High Nibble: **DPI Slot** | Low Nibble: **Polling Rate**. |
| **3** | `Debounce` | `uint8` | Button debounce latency in milliseconds. |
| **4** | `Reserved` | `uint8` | Usually `00`. |
| **5** | `DPI LSB` | `uint8` | Low byte of calculated DPI value. |
| **6** | `DPI MSB` | `uint8` | High byte of calculated DPI value. |
| **7** | `Advanced` | `bitfield` | Sensor toggles (e.g., Motion Sync). |
| **8-31**| `Padding` | `null` | Reserved for future firmware/macro expansion. |

---

### 1.2 Component Decoding Logic

#### A. Active DPI Slot & Polling Rate (Byte 2)
This byte must be masked to extract the two distinct settings:

* **Active Slot Index:** `(Byte2 >> 4)`
    * `0`: Slot 1
    * `1`: Slot 2
    * `2`: Slot 3
    * `3`: Slot 4
    * `4`: Slot 5
    * `5`: Slot 6
* **Polling Rate Index:** `(Byte2 & 0x0F)`
    * `0`: 1000 Hz
    * `1`: 500 Hz
    * `2`: 250 Hz
    * `3`: 125 Hz

#### B. DPI Calculation (Bytes 5 & 6)
The DPI is transmitted as a 16-bit Little Endian integer representing 50-DPI increments, with a `-1` offset.

**Formula:** $$DPI = (((MSB \ll 8) \mid LSB) + 1) \times 50$$

**Example Parse:** Input: `0f 0f` (Lower values often mirror LSB in MSB placeholder)  
Calculation: `(15 + 1) * 50 = 800 DPI`

#### C. Sensor Flags (Byte 7)
* `0x11`: Motion Sync **ON** / Default Performance.
* `0x10`: Motion Sync **OFF**.
* *Note: Lower bits may toggle based on Lift-Off Distance (LOD) settings.*

---

### 1.3 Python Implementation Example

```python
def parse_heartbeat(data):
    # data[0] is Report ID 09
    battery = data[1]
    
    # Byte 2 Split
    slot_idx = (data[2] >> 4)
    poll_idx = (data[2] & 0x0F)
    
    debounce = data[3]
    
    # DPI Reconstruction
    raw_dpi = (data[6] << 8) | data[5]
    actual_dpi = (raw_dpi + 1) * 50
    
    return {
        "battery": battery,
        "slot": slot_idx + 1,
        "polling_hz": {0: 1000, 1: 500, 2: 250, 3: 125}.get(poll_idx),
        "debounce_ms": debounce,
        "dpi": actual_dpi,
        "motion_sync": bool(data[7] & 0x01)
    }
```
---

## 2. Write Commands (PC → Mouse)
Sent as 9-byte Feature Reports (ID `09`).

### A. Active Slot Switching
To switch the active DPI slot without changing the values stored in them:
**Structure:** `09 03 06 [Slot] 00 00 00 00 00`

| Target | Hex [Slot] | Full Command |
| :--- | :--- | :--- |
| Slot 1 | `00` | `09 03 06 00 00 00 00 00 00` |
| Slot 5 | `04` | `09 03 06 04 00 00 00 00 00` |

### B. DPI Value Configuration (Slot Overwrite)
**Structure:** `09 02 [SlotIndex] [LSB] [MSB] 00 00 00 00`
*Note: SlotIndex for writing values starts at `01`.*

| Target | Hex [Index] | Example: Set to 32,000 DPI (`7f 02`) |
| :--- | :--- | :--- |
| Slot 1 | `01` | `09 02 01 7f 02 00 00 00 00` |
| Slot 5 | `05` | `09 02 05 7f 02 00 00 00 00` |

### C. Polling Rate
**Structure:** `09 01 [Value] 00 00 00 00 00 00`
* `00`: 1000 Hz
* `01`: 500 Hz
* `02`: 250 Hz

### D. Hardware Latency & Sensors
**Structure:** `09 05 [Sub-ID] [Value] 00 00 00 00 00`
* **Debounce (Sub `01`):** `09 05 01 [ms] 00 00 00 00 00`
* **Sleep (Sub `03`):** `09 05 03 [secs] 00 00 00 00 00`
* **LOD (Action `04`):** `09 04 01 [01/02] 00 00 00 00 00`

---

## 3. The Sync Request
To force the mouse to push its current status to the PC:
**Command:** `09 06 09 00 00 00 00 00 00`