"""Transport abstraction for HID communication."""

from __future__ import annotations

from abc import ABC, abstractmethod

from incott_configurator.domain.models import DeviceInfo


class HidTransport(ABC):
    @abstractmethod
    def find_management_device(self) -> DeviceInfo | None:
        """Locate the best candidate management interface."""

    @abstractmethod
    def open(self, device_path: str) -> None:
        """Open HID endpoint."""

    @abstractmethod
    def send_feature_report(self, report: bytes) -> int:
        """Write a feature report and return underlying write result."""

    @abstractmethod
    def read(self, size: int = 64, timeout_ms: int = 150) -> bytes:
        """Read input report bytes."""

    @abstractmethod
    def close(self) -> None:
        """Close transport."""
