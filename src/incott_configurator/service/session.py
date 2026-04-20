"""Session manager coordinating transport, sync, parsing, and app snapshot."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field

from incott_configurator.constants import HEARTBEAT_MIN_LENGTH
from incott_configurator.domain.models import AppSnapshot, HeartbeatStatus
from incott_configurator.protocol.commands import build_sync_request
from incott_configurator.protocol.heartbeat import HeartbeatParseError, parse_heartbeat
from incott_configurator.transport.base import HidTransport


@dataclass(slots=True)
class SessionManager:
    transport: HidTransport
    sync_interval_seconds: float = 0.5
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    _snapshot_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _command_queue: queue.SimpleQueue[bytes] = field(
        default_factory=queue.SimpleQueue, init=False
    )
    _snapshot: AppSnapshot = field(
        default_factory=lambda: AppSnapshot(
            connected=False,
            device_mode=None,
            status=None,
            last_error=None,
        ),
        init=False,
    )

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="incott-session", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.transport.close()

    def snapshot(self) -> AppSnapshot:
        with self._snapshot_lock:
            return self._snapshot

    def apply_command(self, command: bytes) -> None:
        """Enqueue a command for the session thread to send; thread-safe."""
        self._command_queue.put_nowait(command)

    def _run(self) -> None:
        try:
            device = self.transport.find_management_device()
            if device is None:
                self._set_disconnected("mouse not found")
                return

            self.transport.open(device.path)
            self._set_connected(device.mode)

            self.transport.send_feature_report(build_sync_request())
            last_sync = time.monotonic()

            while not self._stop_event.is_set():
                # Drain any commands queued by the UI before reading.
                try:
                    while True:
                        cmd = self._command_queue.get_nowait()
                        self.transport.send_feature_report(cmd)
                except queue.Empty:
                    pass

                if time.monotonic() - last_sync >= self.sync_interval_seconds:
                    self.transport.send_feature_report(build_sync_request())
                    last_sync = time.monotonic()

                packet = self.transport.read(size=64, timeout_ms=150)
                if packet and len(packet) >= HEARTBEAT_MIN_LENGTH:
                    try:
                        self._set_status(parse_heartbeat(packet))
                    except HeartbeatParseError:
                        # Ignore malformed packets and keep the session alive.
                        pass

                time.sleep(0.05)

        except HeartbeatParseError as exc:
            self._set_error(f"heartbeat parse error: {exc}")
        except Exception as exc:  # noqa: BLE001
            self._set_error(str(exc))
        finally:
            self.transport.close()

    def _set_connected(self, mode: str) -> None:
        with self._snapshot_lock:
            self._snapshot = AppSnapshot(
                connected=True,
                device_mode=mode,
                status=self._snapshot.status,
                last_error=None,
            )

    def _set_status(self, status: HeartbeatStatus) -> None:
        with self._snapshot_lock:
            self._snapshot = AppSnapshot(
                connected=True,
                device_mode=self._snapshot.device_mode,
                status=status,
                last_error=None,
            )

    def _set_error(self, message: str) -> None:
        with self._snapshot_lock:
            self._snapshot = AppSnapshot(
                connected=False,
                device_mode=self._snapshot.device_mode,
                status=self._snapshot.status,
                last_error=message,
            )

    def _set_disconnected(self, message: str) -> None:
        with self._snapshot_lock:
            self._snapshot = AppSnapshot(
                connected=False,
                device_mode=None,
                status=None,
                last_error=message,
            )
