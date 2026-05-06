import time

from incott_configurator.app.tui import IncottConfiguratorApp
from incott_configurator.domain.models import AppSnapshot, HeartbeatStatus
from incott_configurator.domain.models import PollingRate


class FakeSelect:
    BLANK = object()

    def __init__(self, value):
        self.value = value
        self.has_focus = False


class FakeInput:
    def __init__(self, value):
        self.value = value
        self.has_focus = False


class FakeSession:
    def snapshot(self):
        return AppSnapshot(connected=False, device_mode=None, status=None, last_error=None)


def make_status(slot_index: int) -> HeartbeatStatus:
    return HeartbeatStatus(
        battery_percent=90,
        slot_index=slot_index,
        polling=PollingRate.HZ_1000,
        debounce_ms=4,
        dpi_x=800,
        dpi_y=800,
        motion_sync_enabled=False,
        advanced_flags=0,
        raw_packet=b"",
    )


def test_pending_clears_on_confirmation(monkeypatch):
    app = IncottConfiguratorApp(session=FakeSession())

    # Provide fake widgets for query_one
    widgets = {
        "#select-current-slot": FakeSelect(2),
        "#select-polling": FakeSelect(int(PollingRate.HZ_1000)),
        "#input-debounce": FakeInput("4"),
        "#select-lod": FakeSelect(1),
        "#input-sleep": FakeInput("300"),
        "#select-edit-slot": FakeSelect(2),
        "#input-dpi-x": FakeInput("400"),
        "#input-dpi-y": FakeInput("400"),
    }

    def query_one(selector, _type=None):
        return widgets[selector]

    monkeypatch.setattr(app, "query_one", query_one)

    # Simulate a user-initiated switch to slot 3
    app._current_slot_pending = 3
    app._current_slot_pending_at = time.monotonic() - 1

    # Heartbeat reports slot_index == 2 (slot 3)
    status = make_status(slot_index=2)

    app._hydrate_controls_from_status(status)

    assert app._current_slot_pending is None
    assert app._current_slot_dirty is False


def test_pending_timeout_reverts(monkeypatch):
    app = IncottConfiguratorApp(session=FakeSession())

    widgets = {
        "#select-current-slot": FakeSelect(3),
        "#select-polling": FakeSelect(int(PollingRate.HZ_1000)),
        "#input-debounce": FakeInput("4"),
        "#select-lod": FakeSelect(1),
        "#input-sleep": FakeInput("300"),
        "#select-edit-slot": FakeSelect(2),
        "#input-dpi-x": FakeInput("400"),
        "#input-dpi-y": FakeInput("400"),
    }

    def query_one(selector, _type=None):
        return widgets[selector]

    monkeypatch.setattr(app, "query_one", query_one)

    # Pending switch to 3 but timestamp is old
    app._current_slot_pending = 3
    app._current_slot_pending_at = time.monotonic() - 10

    # Heartbeat still reports slot_index 1 (slot 2)
    status = make_status(slot_index=1)

    app._hydrate_controls_from_status(status)

    # Pending should be cleared due to timeout and select updated to device slot (2)
    assert app._current_slot_pending is None
    assert app._current_slot_dirty is False
    assert widgets["#select-current-slot"].value == 2
