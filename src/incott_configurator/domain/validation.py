"""Input validation and conversion helpers for writable settings."""

from __future__ import annotations

from incott_configurator.domain.models import PollingRate


def validate_slot_index(slot_index: int, *, write_indexed_from_one: bool = False) -> int:
    lower, upper = (1, 6) if write_indexed_from_one else (0, 5)
    if not (lower <= slot_index <= upper):
        raise ValueError(f"slot index must be in [{lower}, {upper}], got {slot_index}")
    return slot_index


def validate_dpi(dpi: int) -> int:
    if dpi < 50 or dpi > 32000:
        raise ValueError(f"dpi must be in [50, 32000], got {dpi}")
    if dpi % 50 != 0:
        raise ValueError(f"dpi must be multiple of 50, got {dpi}")
    return dpi


def dpi_to_raw_pair(dpi: int) -> tuple[int, int]:
    validated = validate_dpi(dpi)
    raw_value = (validated // 50) - 1
    lsb = raw_value & 0xFF
    msb = (raw_value >> 8) & 0xFF
    return lsb, msb


def validate_polling_rate(raw_value: int) -> PollingRate:
    try:
        return PollingRate(raw_value)
    except ValueError as exc:
        raise ValueError(f"invalid polling rate index: {raw_value}") from exc


def validate_debounce_ms(value: int) -> int:
    if value < 0 or value > 31:
        raise ValueError(f"debounce must be in [0, 31] ms, got {value}")
    return value


def validate_sleep_seconds(value: int) -> int:
    if value < 0 or value > 255:
        raise ValueError(f"sleep seconds must be in [0, 255], got {value}")
    return value
