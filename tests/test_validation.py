from __future__ import annotations

import pytest

from incott_configurator.domain.validation import (
    dpi_to_raw_pair,
    validate_debounce_ms,
    validate_dpi,
    validate_sleep_seconds,
    validate_slot_index,
)


def test_validate_slot_index_ranges() -> None:
    assert validate_slot_index(0) == 0
    assert validate_slot_index(6, write_indexed_from_one=True) == 6
    with pytest.raises(ValueError):
        validate_slot_index(6)


def test_validate_dpi_and_conversion() -> None:
    assert validate_dpi(800) == 800
    assert dpi_to_raw_pair(800) == (0x0F, 0x00)
    with pytest.raises(ValueError):
        validate_dpi(775)


def test_validate_debounce() -> None:
    assert validate_debounce_ms(0) == 0
    assert validate_debounce_ms(31) == 31
    with pytest.raises(ValueError):
        validate_debounce_ms(32)


def test_validate_sleep_seconds() -> None:
    assert validate_sleep_seconds(0) == 0
    assert validate_sleep_seconds(255) == 255
    with pytest.raises(ValueError):
        validate_sleep_seconds(256)
