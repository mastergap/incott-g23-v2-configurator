"""Production HID transport using python hidapi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from incott_configurator.constants import SUPPORTED_PRODUCTS, VENDOR_ID
from incott_configurator.domain.models import DeviceInfo
from incott_configurator.transport.base import HidTransport


@dataclass(slots=True)
class HidApiAdapter(HidTransport):
    """hidapi-backed transport.

    This adapter is intentionally small so protocol/session logic stays testable.
    """

    debug: bool = False

    def __post_init__(self) -> None:
        try:
            import hid  # type: ignore
        except ImportError as exc:
            raise RuntimeError("hidapi is not installed") from exc

        self._hid: Any = hid
        self._device: Any | None = None

    def find_management_device(self) -> DeviceInfo | None:
        devices = self._hid.enumerate()
        candidates: list[dict[str, Any]] = []

        for dev in devices:
            vendor_id = int(dev.get("vendor_id", 0))
            product_id = int(dev.get("product_id", 0))
            if vendor_id != VENDOR_ID:
                continue
            if product_id not in SUPPORTED_PRODUCTS:
                continue
            candidates.append(dev)

        if not candidates:
            return None

        candidates.sort(key=lambda item: int(item.get("interface_number", 0) or 0))
        selected = candidates[-1]

        raw_path = selected.get("path")
        if isinstance(raw_path, bytes):
            path = raw_path.decode("utf-8", errors="ignore")
        elif isinstance(raw_path, str):
            path = raw_path
        else:
            raise RuntimeError("hidapi returned unsupported path type")

        product_id = int(selected["product_id"])
        interface_number_raw = selected.get("interface_number")
        interface_number: int | None
        if interface_number_raw is None:
            interface_number = None
        else:
            interface_number = int(interface_number_raw)

        return DeviceInfo(
            path=path,
            product_id=product_id,
            mode=SUPPORTED_PRODUCTS[product_id],
            interface_number=interface_number,
        )

    def open(self, device_path: str) -> None:
        device = self._hid.device()
        device.open_path(device_path.encode("utf-8"))
        device.set_nonblocking(True)
        self._device = device

    def send_feature_report(self, report: bytes) -> int:
        if self._device is None:
            raise RuntimeError("device is not open")
        return int(self._device.send_feature_report(list(report)))

    def read(self, size: int = 64, timeout_ms: int = 150) -> bytes:
        if self._device is None:
            raise RuntimeError("device is not open")

        data = self._device.read(size, timeout_ms)
        return bytes(data) if data else b""

    def close(self) -> None:
        if self._device is not None:
            self._device.close()
            self._device = None
