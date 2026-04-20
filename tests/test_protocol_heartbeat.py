from __future__ import annotations

import pytest

from incott_configurator.protocol.heartbeat import HeartbeatParseError, parse_heartbeat


def test_parse_heartbeat_happy_path_symmetric_dpi() -> None:
    # byte4=0x00 → no multiplier; byte5=byte6=0x0F → 800 DPI on both axes
    packet = bytes([
        0x09,
        75,
        0x12,
        4,
        0x00,
        0x0F,
        0x0F,
        0x11,
        *([0x00] * 24),
    ])

    status = parse_heartbeat(packet)

    assert status.battery_percent == 75
    assert status.slot_index == 1
    assert status.polling.hz == 250
    assert status.debounce_ms == 4
    assert status.dpi_x == 800
    assert status.dpi_y == 800
    assert status.motion_sync_enabled is True


def test_parse_heartbeat_high_dpi_with_multiplier() -> None:
    # byte4=0x11 → both nibbles non-zero → ×5 multiplier on both axes
    # byte5=byte6=0x7F → (127+1)*50*5 = 32000 DPI
    packet = bytes([
        0x09,
        90,
        0x00,
        2,
        0x11,
        0x7F,
        0x7F,
        0x10,
        *([0x00] * 24),
    ])

    status = parse_heartbeat(packet)

    assert status.dpi_x == 32000
    assert status.dpi_y == 32000
    assert status.motion_sync_enabled is False


def test_parse_heartbeat_invalid_report_id() -> None:
    packet = bytes([0x08, *([0x00] * 31)])
    with pytest.raises(HeartbeatParseError):
        parse_heartbeat(packet)


def test_parse_heartbeat_short_packet() -> None:
    packet = bytes([0x09, 0x00])
    with pytest.raises(HeartbeatParseError):
        parse_heartbeat(packet)


def test_parse_heartbeat_compact_packet_is_accepted() -> None:
    packet = bytes([0x09, 50, 0x00, 4, 0x00, 0x0F, 0x0F, 0x10])
    status = parse_heartbeat(packet)

    assert status.battery_percent == 50
    assert status.dpi_x == 800
    assert status.dpi_y == 800
    assert status.motion_sync_enabled is False


def test_parse_heartbeat_without_report_id_is_accepted() -> None:
    # Layout is heartbeat payload without leading 0x09 report id.
    packet = bytes([50, 0x00, 4, 0x00, 0x0F, 0x0F, 0x10, *([0x00] * 24)])

    status = parse_heartbeat(packet)

    assert status.battery_percent == 50
    assert status.slot_index == 0
    assert status.debounce_ms == 4
    assert status.dpi_x == 800
    assert status.dpi_y == 800


def test_parse_heartbeat_with_leading_zero_padding_is_accepted() -> None:
    # Some stacks may expose a leading padding byte before report id.
    packet = bytes([0x00, 0x09, 50, 0x00, 4, 0x00, 0x0F, 0x0F, 0x10, *([0x00] * 23)])

    status = parse_heartbeat(packet)

    assert status.battery_percent == 50
    assert status.slot_index == 0
    assert status.dpi_x == 800
    assert status.dpi_y == 800
