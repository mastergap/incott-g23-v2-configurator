from incott_configurator.app.tui import IncottConfiguratorApp
from incott_configurator.domain.models import HeartbeatStatus, PollingRate
from incott_configurator.domain.models import LodLevel, DeviceInfo, AppSnapshot


class DummySession:
    def __init__(self):
        self._snapshot = AppSnapshot(connected=False, device_mode=None, status=None, last_error=None)

    def snapshot(self):
        return self._snapshot

    def apply_command(self, _cmd: bytes) -> None:
        # no-op for tests
        pass


def make_status() -> HeartbeatStatus:
    # minimal valid heartbeat status for the widget hydration
    return HeartbeatStatus(
        battery_percent=100,
        slot_index=0,
        polling=PollingRate.HZ_1000,
        debounce_ms=4,
        dpi_x=400,
        dpi_y=400,
        motion_sync_enabled=False,
        advanced_flags=0,
        raw_packet=b"",
    )


def test_lod_select_not_overwritten_by_heartbeat(monkeypatch):
    """Simulate user selecting new LOD and a heartbeat arriving before saving.

    Expected: the LOD select keeps the user selection until Apply is pressed.
    """
    session = DummySession()
    app = IncottConfiguratorApp(session)

    # Provide fake widgets for query_one
    class FakeSelect:
        BLANK = object()

        def __init__(self, value):
            self.value = value
            self.has_focus = False

    class FakeInput:
        def __init__(self, value):
            self.value = value
            self.has_focus = False

    widgets = {
        "#select-current-slot": FakeSelect(1),
        "#select-polling": FakeSelect(int(PollingRate.HZ_1000)),
        "#input-debounce": FakeInput("4"),
        "#select-lod": FakeSelect(int(LodLevel.LOW)),
        "#input-sleep": FakeInput("300"),
        "#select-edit-slot": FakeSelect(1),
        "#input-dpi-x": FakeInput("400"),
        "#input-dpi-y": FakeInput("400"),
    }

    def query_one(selector, _type=None):
        return widgets[selector]

    # Monkeypatch the app.query_one to use our fake widgets
    monkeypatch.setattr(app, "query_one", query_one)

    # Initial heartbeat reports LOW
    status = make_status()
    session._snapshot = AppSnapshot(connected=True, device_mode="mode", status=status, last_error=None)
    app._persisted_lod_level = int(LodLevel.LOW)

    # First hydration should set select to LOW
    app._hydrate_controls_from_status(status)
    lod_select = widgets["#select-lod"]
    assert lod_select.value == int(LodLevel.LOW)

    # User changes select to HIGH (dirty)
    lod_select.value = int(LodLevel.HIGH)
    app._lod_dirty = True

    # Before user saves, a heartbeat arrives still reporting LOW
    status2 = make_status()
    session._snapshot = AppSnapshot(connected=True, device_mode="mode", status=status2, last_error=None)
    app._hydrate_controls_from_status(status2)

    # The select should remain HIGH because user hasn't saved yet
    assert lod_select.value == int(LodLevel.HIGH)

    # Now simulate the user pressing Apply which calls _apply_hardware -> clears dirty
    app._persisted_lod_level = int(LodLevel.HIGH)
    app._lod_dirty = False

    # After persisting the new LOD, hydration should reflect the persisted value
    status3 = make_status()
    session._snapshot = AppSnapshot(connected=True, device_mode="mode", status=status3, last_error=None)
    app._hydrate_controls_from_status(status3)
    assert lod_select.value == int(LodLevel.HIGH)
