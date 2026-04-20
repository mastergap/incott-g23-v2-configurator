from __future__ import annotations

from incott_configurator.domain.models import LodLevel, PollingRate
from incott_configurator.protocol.commands import (
    AXIS_BOTH,
    AXIS_X,
    AXIS_Y,
    build_set_debounce_ms,
    build_set_lod,
    build_set_polling_rate,
    build_set_sleep_timeout,
    build_switch_active_slot,
    build_sync_request,
    build_write_slot_dpi,
)


def test_build_switch_active_slot() -> None:
    assert build_switch_active_slot(4) == bytes([0x09, 0x03, 0x06, 0x04, 0, 0, 0, 0, 0])


def test_build_write_slot_dpi_both_axes() -> None:
    # Official capture: slot 6 (index 5), 500 DPI both axes.
    assert build_write_slot_dpi(5, 500, axis=AXIS_BOTH) == bytes(
        [0x09, 0x02, 0x05, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00]
    )


def test_build_write_slot_dpi_axis_specific() -> None:
    # Official capture: slot 5 (index 4), X 32000 then Y 600.
    assert build_write_slot_dpi(4, 32000, axis=AXIS_X) == bytes(
        [0x09, 0x02, 0x04, 0x7F, 0x02, 0x00, 0x00, 0x00, 0x01]
    )
    assert build_write_slot_dpi(4, 600, axis=AXIS_Y) == bytes(
        [0x09, 0x02, 0x04, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x02]
    )


def test_build_set_polling_rate() -> None:
    assert build_set_polling_rate(PollingRate.HZ_500) == bytes([0x09, 0x01, 0x01, 0, 0, 0, 0, 0, 0])


def test_build_set_debounce_ms() -> None:
    assert build_set_debounce_ms(8) == bytes([0x09, 0x05, 0x01, 0x08, 0, 0, 0, 0, 0])


def test_build_set_lod() -> None:
    assert build_set_lod(LodLevel.HIGH) == bytes([0x09, 0x04, 0x01, 0x02, 0, 0, 0, 0, 0])


def test_build_set_sleep_timeout() -> None:
    assert build_set_sleep_timeout(30) == bytes([0x09, 0x05, 0x03, 0x1E, 0, 0, 0, 0, 0])


def test_build_sync_request() -> None:
    assert build_sync_request() == bytes([0x09, 0x06, 0x09, 0, 0, 0, 0, 0, 0])
