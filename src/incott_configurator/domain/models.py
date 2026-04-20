"""Domain models for application state and protocol values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ConnectionMode(str):
    WIRED = "wired"
    WIRELESS = "wireless"


class PollingRate(IntEnum):
    HZ_1000 = 0
    HZ_500 = 1
    HZ_250 = 2
    HZ_125 = 3

    @property
    def hz(self) -> int:
        mapping = {
            PollingRate.HZ_1000: 1000,
            PollingRate.HZ_500: 500,
            PollingRate.HZ_250: 250,
            PollingRate.HZ_125: 125,
        }
        return mapping[self]


class LodLevel(IntEnum):
    LOW = 1
    HIGH = 2


@dataclass(frozen=True, slots=True)
class HeartbeatStatus:
    battery_percent: int
    slot_index: int
    polling: PollingRate
    debounce_ms: int
    dpi_x: int
    dpi_y: int
    motion_sync_enabled: bool
    advanced_flags: int
    raw_packet: bytes


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    path: str
    product_id: int
    mode: str
    interface_number: int | None


@dataclass(frozen=True, slots=True)
class AppSnapshot:
    connected: bool
    device_mode: str | None
    status: HeartbeatStatus | None
    last_error: str | None
