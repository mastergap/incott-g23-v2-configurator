# Incott G23V2SE HID Protocol Specification

**Target Hardware:** Incott Esports G23V2SE (Pixart 3395)
**USB ID:** `093a:622c`
**Interface:** Linux `/dev/hidraw` (Management Node)

## 0. Connectivity Detection
The software distinguishes between connection modes via the USB Product ID (PID):

| Mode         | Product ID (Hex) | Product ID (Dec) |
| :----------- | :--------------- | :--------------- |
| **Wired**    | `622c`           | `25132`          |
| **Wireless** | `522c`           | `21036`          |

**Detection Logic:** Applications should filter for Vendor ID `093a` and then check the PID to toggle UI elements (e.g., hiding battery status when wired, or showing a signal strength icon when wireless). The interface that sends the hearthbeat messages is the one with the higher number (usually 2).

## 1. The Inbound Heartbeat (Status Report)
The mouse broadcasts a 32-byte status message whenever its state changes or a sync is requested. This allows a TUI to reflect the physical state of the hardware in real-time.

**Report ID:** `09`  
**Payload Length:** 32 Bytes  
**Trigger:** The mouse is sending a report by himself. OLD behavior: Sent by hardware on DPI button press, physical connection change, or via `09 06 09` sync request.

### 1.1 Byte-by-Byte Memory Map

| Offset   | Name          | Type       | Description                                          |
| :------- | :------------ | :--------- | :--------------------------------------------------- |
| **0**    | `Report ID`   | `uint8`    | Always `09`.                                         |
| **1**    | `Battery`     | `uint8`    | Battery percentage (0-100 decimal).                  |
| **2**    | `Slot & Poll` | `bitfield` | High Nibble: **DPI Slot**                            | Low Nibble: **Polling Rate**.   |
| **3**    | `Debounce`    | `uint8`    | Button debounce latency in milliseconds.             |
| **4**    | `DPI Mult`    | `bitfield` | Low Nibble: X multiplier flag                        | High Nibble: Y multiplier flag. |
| **5**    | `DPI X Raw`   | `uint8`    | Base X DPI value in 50-DPI increments (`+1` offset). |
| **6**    | `DPI Y Raw`   | `uint8`    | Base Y DPI value in 50-DPI increments (`+1` offset). |
| **7**    | `Advanced`    | `bitfield` | Sensor toggles (e.g., Motion Sync).                  |
| **8-31** | `Padding`     | `null`     | Reserved for future firmware/macro expansion.        |

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

#### B. DPI Calculation (Bytes 4, 5, 6)
The DPI for X and Y is calculated independently using byte 4 multiplier flags.

* `mult_x = 5` if `(Byte4 & 0x0F) > 0`, else `1`
* `mult_y = 5` if `(Byte4 >> 4) > 0`, else `1`
* `dpi_x = (Byte5 + 1) * 50 * mult_x`
* `dpi_y = (Byte6 + 1) * 50 * mult_y`

**Examples:**
* `Byte4=00, Byte5=0f, Byte6=0f` -> `dpi_x=800, dpi_y=800`
* `Byte4=11, Byte5=7f, Byte6=7f` -> `dpi_x=32000, dpi_y=32000`

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

    # DPI Reconstruction (per axis)
    mult_x = 5 if (data[4] & 0x0F) > 0 else 1
    mult_y = 5 if (data[4] >> 4) > 0 else 1
    dpi_x = (data[5] + 1) * 50 * mult_x
    dpi_y = (data[6] + 1) * 50 * mult_y
    
    return {
        "battery": battery,
        "slot": slot_idx + 1,
        "polling_hz": {0: 1000, 1: 500, 2: 250, 3: 125}.get(poll_idx),
        "debounce_ms": debounce,
        "dpi_x": dpi_x,
        "dpi_y": dpi_y,
        "motion_sync": bool(data[7] & 0x01)
    }
```
---

## 2. Write Commands (PC → Mouse)
Sent as 9-byte Feature Reports (ID `09`).

### A. Active Slot Switching
To switch the active DPI slot without changing the values stored in them:
**Structure:** `09 03 06 [Slot] 00 00 00 00 00`

| Target | Hex [Slot] | Full Command                 |
| :----- | :--------- | :--------------------------- |
| Slot 1 | `00`       | `09 03 06 00 00 00 00 00 00` |
| Slot 5 | `04`       | `09 03 06 04 00 00 00 00 00` |

### B. DPI Value Configuration (Slot Overwrite)
**Confirmed Structure (from official app capture):**
`09 02 [SlotIndex0] [LSB] [MSB] 00 00 00 [Axis]`

* `SlotIndex0` is **zero-based** (`00` = Slot 1, `05` = Slot 6).
* `Axis` selector:
    * `00`: write both X and Y to the same DPI value
    * `01`: write only X axis DPI
    * `02`: write only Y axis DPI

**Captured Examples**

| Scenario                   | Packet                       |
| :------------------------- | :--------------------------- |
| Slot 6, 500 DPI both X/Y   | `09 02 05 09 00 00 00 00 00` |
| Slot 6, 32000 DPI both X/Y | `09 02 05 7f 02 00 00 00 00` |
| Slot 5, 32000 DPI X only   | `09 02 04 7f 02 00 00 00 01` |
| Slot 5, 600 DPI Y only     | `09 02 04 0b 00 00 00 00 02` |

### C. Polling Rate
**Structure:** `09 01 [Value] 00 00 00 00 00 00`
* `00`: 1000 Hz
* `01`: 500 Hz
* `02`: 250 Hz
* `03`: 125 Hz

### D. Hardware Latency & Sensors
**Structure:** `09 05 [Sub-ID] [Value] 00 00 00 00 00`
* **Debounce (Sub `01`):** `09 05 01 [ms] 00 00 00 00 00`
* **Sleep (Sub `03`):** `09 05 03 [secs] 00 00 00 00 00`
* **LOD (Action `04`):** `09 04 01 [01/02] 00 00 00 00 00`

---

## 3. The Sync Request
To force the mouse to push its current status to the PC:
**Command:** `09 06 09 00 00 00 00 00 00`