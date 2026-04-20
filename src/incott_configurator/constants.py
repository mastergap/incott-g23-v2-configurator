"""Project-wide constants."""

from __future__ import annotations

VENDOR_ID = 0x093A
SUPPORTED_PRODUCTS: dict[int, str] = {
    0x622C: "wired",
    0x522C: "wireless",
}

REPORT_ID = 0x09
HEARTBEAT_LENGTH = 32
HEARTBEAT_MIN_LENGTH = 8
FEATURE_REPORT_LENGTH = 9

SYNC_REQUEST = bytes([0x09, 0x06, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
