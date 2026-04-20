"""Heartbeat packet parser (Report ID 0x09)."""

from __future__ import annotations

from incott_configurator.constants import HEARTBEAT_LENGTH, HEARTBEAT_MIN_LENGTH, REPORT_ID
from incott_configurator.domain.models import HeartbeatStatus
from incott_configurator.domain.validation import validate_polling_rate


class HeartbeatParseError(ValueError):
    """Raised when heartbeat parsing fails."""


def _normalize_heartbeat_packet(packet: bytes) -> bytes:
    if len(packet) < HEARTBEAT_MIN_LENGTH:
        raise HeartbeatParseError(
            f"expected at least {HEARTBEAT_MIN_LENGTH} bytes, got {len(packet)}"
        )

    # Native layout: report id is the first byte.
    if packet[0] == REPORT_ID:
        return packet

    # Some backends prepend a zero byte before report id.
    if len(packet) >= HEARTBEAT_MIN_LENGTH + 1 and packet[0] == 0x00 and packet[1] == REPORT_ID:
        return packet[1:]

    # Some backends return input reports without report id; infer by heartbeat shape.
    battery = packet[0]
    slot_poll = packet[1]
    debounce = packet[2]
    advanced_flags = packet[6]
    slot = (slot_poll >> 4) & 0x0F
    poll = slot_poll & 0x0F
    if (
        battery <= 100
        and slot <= 5
        and poll <= 3
        and debounce <= 31
        and (advanced_flags & 0xF0) == 0x10
    ):
        return bytes([REPORT_ID]) + packet

    raise HeartbeatParseError(
        f"invalid report id: expected 0x{REPORT_ID:02x}, got 0x{packet[0]:02x}"
    )


def parse_heartbeat(packet: bytes) -> HeartbeatStatus:
    normalized = _normalize_heartbeat_packet(packet)

    battery = normalized[1]
    slot_index = (normalized[2] >> 4) & 0x0F
    polling = validate_polling_rate(normalized[2] & 0x0F)
    debounce = normalized[3]

    # Byte 4 carries separate multiplier flags for X and Y axes.
    # Low nibble → X multiplier, high nibble → Y multiplier.
    # A non-zero nibble means ×5; zero means ×1.
    mult_x = 5 if (normalized[4] & 0x0F) > 0 else 1
    mult_y = 5 if (normalized[4] >> 4) > 0 else 1
    dpi_x = (normalized[5] + 1) * 50 * mult_x
    dpi_y = (normalized[6] + 1) * 50 * mult_y

    advanced_flags = normalized[7]
    motion_sync = bool(advanced_flags & 0x01)

    return HeartbeatStatus(
        battery_percent=battery,
        slot_index=slot_index,
        polling=polling,
        debounce_ms=debounce,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        motion_sync_enabled=motion_sync,
        advanced_flags=advanced_flags,
        raw_packet=(
            normalized[:HEARTBEAT_LENGTH]
            if len(normalized) >= HEARTBEAT_LENGTH
            else normalized
        ),
    )
