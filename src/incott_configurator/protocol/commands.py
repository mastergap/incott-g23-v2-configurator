"""Feature-report command encoders for known writable settings."""

from __future__ import annotations

from incott_configurator.constants import FEATURE_REPORT_LENGTH, REPORT_ID
from incott_configurator.domain.models import LodLevel, PollingRate
from incott_configurator.domain.validation import (
    dpi_to_raw_pair,
    validate_debounce_ms,
    validate_sleep_seconds,
    validate_slot_index,
)

AXIS_BOTH = 0x00
AXIS_X = 0x01
AXIS_Y = 0x02


def _frame(*payload: int) -> bytes:
    data = [REPORT_ID, *payload]
    if len(data) > FEATURE_REPORT_LENGTH:
        raise ValueError(f"feature report exceeds {FEATURE_REPORT_LENGTH} bytes")
    data.extend([0x00] * (FEATURE_REPORT_LENGTH - len(data)))
    return bytes(data)


def build_switch_active_slot(slot_index_zero_based: int) -> bytes:
    slot = validate_slot_index(slot_index_zero_based, write_indexed_from_one=False)
    return _frame(0x03, 0x06, slot)


def build_write_slot_dpi(
    slot_index_zero_based: int,
    dpi: int,
    *,
    axis: int = AXIS_BOTH,
) -> bytes:
    """Build DPI slot write.

    Confirmed packet shape from official app captures:
    `09 02 [slot_zero_based] [LSB] [MSB] 00 00 00 [axis]`
    where axis is 00 (both), 01 (X), 02 (Y).
    """
    slot = validate_slot_index(slot_index_zero_based, write_indexed_from_one=False)
    if axis not in {AXIS_BOTH, AXIS_X, AXIS_Y}:
        raise ValueError(f"invalid axis selector: {axis}")
    lsb, msb = dpi_to_raw_pair(dpi)
    return _frame(0x02, slot, lsb, msb, 0x00, 0x00, 0x00, axis)


def build_set_polling_rate(polling: PollingRate) -> bytes:
    return _frame(0x01, int(polling))


def build_set_debounce_ms(debounce_ms: int) -> bytes:
    value = validate_debounce_ms(debounce_ms)
    return _frame(0x05, 0x01, value)


def build_set_lod(level: LodLevel) -> bytes:
    return _frame(0x04, 0x01, int(level))


def build_set_sleep_timeout(seconds: int) -> bytes:
    value = validate_sleep_seconds(seconds)
    return _frame(0x05, 0x03, value)


def build_sync_request() -> bytes:
    return _frame(0x06, 0x09)
