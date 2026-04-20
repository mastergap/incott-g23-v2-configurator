"""Textual UI application shell."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from incott_configurator.domain.models import LodLevel, PollingRate
from incott_configurator.domain.validation import (
    validate_debounce_ms,
    validate_dpi,
    validate_sleep_seconds,
)
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
from incott_configurator.service.local_settings import LocalSettingsState, LocalSettingsStore
from incott_configurator.service.session import SessionManager

_DEFAULT_SLOT_DPI_VALUES: dict[int, tuple[int, int]] = {
    1: (400, 400),
    2: (800, 800),
    3: (1600, 1600),
    4: (2400, 2400),
    5: (3200, 3200),
    6: (6400, 6400),
}


class CurrentSettingsWidget(Static):
    """Live table of settings received from the mouse heartbeat."""

    DEFAULT_CSS = """
    CurrentSettingsWidget {
        padding: 1 2;
    }
    """

    # Row order must match _VALUES_COUNT and refresh_from_snapshot.
    _ROWS: list[tuple[str, str]] = [
        ("Connection Mode", "heartbeat"),
        ("Battery", "heartbeat"),
        ("Active Slot", "heartbeat"),
        ("DPI X", "heartbeat"),
        ("DPI Y", "heartbeat"),
        ("Polling Rate", "heartbeat"),
        ("Debounce", "heartbeat"),
        ("Motion Sync", "heartbeat"),
        ("LOD", "local cache"),
        ("Sleep Timeout", "local cache"),
    ]
    # Column index for the live "Value" column.
    _VALUE_COL = 1

    def compose(self) -> ComposeResult:
        table: DataTable[str] = DataTable(id="settings-table", show_cursor=False)
        table.can_focus = False
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#settings-table", DataTable)
        table.add_columns("Setting", "Value", "Source")
        for label, source in self._ROWS:
            table.add_row(label, "—", source)

    def _set_values(self, values: list[str]) -> None:
        table = self.query_one("#settings-table", DataTable)
        for row_index, value in enumerate(values):
            table.update_cell_at(Coordinate(row_index, self._VALUE_COL), value)

    def refresh_from_snapshot(
        self,
        connected: bool,
        device_mode: str | None,
        status: object,
        lod_level: int | None,
        sleep_timeout_seconds: int | None,
    ) -> None:
        from incott_configurator.domain.models import HeartbeatStatus

        if not connected or not isinstance(status, HeartbeatStatus):
            self._set_values([
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                self._format_lod(lod_level),
                self._format_sleep_timeout(sleep_timeout_seconds),
            ])
            return

        self._set_values([
            device_mode or "—",
            f"{status.battery_percent}%",
            str(status.slot_index + 1),
            str(status.dpi_x),
            str(status.dpi_y),
            f"{status.polling.hz} Hz",
            f"{status.debounce_ms} ms",
            "on" if status.motion_sync_enabled else "off",
            self._format_lod(lod_level),
            self._format_sleep_timeout(sleep_timeout_seconds),
        ])

    def _format_lod(self, lod_level: int | None) -> str:
        if lod_level == int(LodLevel.LOW):
            return "Low"
        if lod_level == int(LodLevel.HIGH):
            return "High"
        return "—"

    def _format_sleep_timeout(self, sleep_timeout_seconds: int | None) -> str:
        if sleep_timeout_seconds is None:
            return "—"
        return f"{sleep_timeout_seconds} s"


_SLOT_OPTIONS = [(f"Slot {i}", i) for i in range(1, 7)]
_POLLING_OPTIONS = [
    ("1000 Hz", int(PollingRate.HZ_1000)),
    ("500 Hz", int(PollingRate.HZ_500)),
    ("250 Hz", int(PollingRate.HZ_250)),
    ("125 Hz", int(PollingRate.HZ_125)),
]
_LOD_OPTIONS = [("Low", int(LodLevel.LOW)), ("High", int(LodLevel.HIGH))]


class IncottConfiguratorApp(App[None]):
    CSS = """
    Screen { layout: vertical; }

    #status-bar {
        height: 3;
        padding: 1 2;
        background: $surface;
        border-bottom: tall $primary;
        color: $text;
    }

    #current-settings-panel {
        height: 14;
        border-bottom: tall $primary-background;
    }

    .pane {
        padding: 1 2;
    }

    .field-row {
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }

    .field-label {
        width: 22;
    }

    .field-control {
        width: 28;
    }

    .apply-row {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, session: SessionManager) -> None:
        super().__init__()
        self._session = session
        self._settings_store = LocalSettingsStore()
        persisted_state = self._settings_store.load()
        self._slot_dpi_values: dict[int, tuple[int, int]] = {
            **_DEFAULT_SLOT_DPI_VALUES,
            **persisted_state.slot_dpi_values,
        }
        self._persisted_lod_level = persisted_state.lod_level
        self._persisted_sleep_timeout_seconds = persisted_state.sleep_timeout_seconds
        self._current_slot_initialized = False
        self._last_hydrated_slot: int | None = None
        self._current_slot_pending: int | None = None
        self._polling_pending: PollingRate | None = None
        self._current_slot_dirty = False
        self._polling_dirty = False
        self._dpi_edit_dirty = False
        self._dpi_pending: tuple[int, int, int] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Connecting...", id="status-bar")
        with Vertical(id="current-settings-panel"):
            yield CurrentSettingsWidget(id="current-settings")
        with TabbedContent():
            with TabPane("Slot & DPI", id="tab-dpi"):
                with Vertical(classes="pane"):
                    with Horizontal(classes="field-row"):
                        yield Label("Current Slot", classes="field-label")
                        yield Select(
                            _SLOT_OPTIONS,
                            value=1,
                            id="select-current-slot",
                            classes="field-control",
                        )
                    with Horizontal(classes="apply-row"):
                        yield Button("Switch Slot", id="btn-switch-slot", variant="primary")
                    with Horizontal(classes="field-row"):
                        yield Label("Edit Slot", classes="field-label")
                        yield Select(
                            _SLOT_OPTIONS,
                            value=1,
                            id="select-edit-slot",
                            classes="field-control",
                        )
                    with Horizontal(classes="field-row"):
                        yield Label("DPI X", classes="field-label")
                        yield Input("400", id="input-dpi-x", type="integer", classes="field-control")
                    with Horizontal(classes="field-row"):
                        yield Label("DPI Y", classes="field-label")
                        yield Input("400", id="input-dpi-y", type="integer", classes="field-control")
                    with Horizontal(classes="apply-row"):
                        yield Button("Save Slot DPI", id="btn-save-slot-dpi", variant="primary")
            with TabPane("Polling Rate", id="tab-polling"):
                with Vertical(classes="pane"):
                    with Horizontal(classes="field-row"):
                        yield Label("Polling Rate", classes="field-label")
                        yield Select(
                            _POLLING_OPTIONS, value=int(PollingRate.HZ_1000),
                            id="select-polling", classes="field-control",
                        )
                    with Horizontal(classes="apply-row"):
                        yield Button("Apply", id="btn-polling", variant="primary")
            with TabPane("Hardware", id="tab-hw"):
                with Vertical(classes="pane"):
                    with Horizontal(classes="field-row"):
                        yield Label("Debounce (ms)", classes="field-label")
                        yield Input("4", id="input-debounce", type="integer", classes="field-control")
                    with Horizontal(classes="field-row"):
                        yield Label("Lift-Off Distance", classes="field-label")
                        yield Select(
                            _LOD_OPTIONS,
                            value=(
                                self._persisted_lod_level
                                if self._persisted_lod_level is not None
                                else int(LodLevel.LOW)
                            ),
                            id="select-lod", classes="field-control",
                        )
                    with Horizontal(classes="field-row"):
                        yield Label("Sleep Timeout (s)", classes="field-label")
                        yield Input(
                            str(self._persisted_sleep_timeout_seconds or 300),
                            id="input-sleep",
                            type="integer",
                            classes="field-control",
                        )
                    with Horizontal(classes="apply-row"):
                        yield Button("Apply", id="btn-hw", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.25, self._refresh_status)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "btn-switch-slot": self._apply_switch_slot,
            "btn-save-slot-dpi": self._apply_slot_dpi,
            "btn-polling": self._apply_polling,
            "btn-hw": self._apply_hardware,
        }
        handler = handlers.get(event.button.id or "")
        if handler:
            handler()

    def _refresh_status(self) -> None:
        snap = self._session.snapshot()
        bar = self.query_one("#status-bar", Static)
        widget = self.query_one("#current-settings", CurrentSettingsWidget)

        if not snap.connected:
            bar.update(f"Disconnected — {snap.last_error or 'searching...'}")
            widget.refresh_from_snapshot(
                False,
                None,
                None,
                self._persisted_lod_level,
                self._persisted_sleep_timeout_seconds,
            )
            return

        if snap.status is None:
            bar.update("Connected — waiting for heartbeat...")
            widget.refresh_from_snapshot(
                True,
                snap.device_mode,
                None,
                self._persisted_lod_level,
                self._persisted_sleep_timeout_seconds,
            )
            return

        st = snap.status
        self._slot_dpi_values[st.slot_index + 1] = (st.dpi_x, st.dpi_y)
        self._hydrate_controls_from_status(st)

        bar.update(
            f"Mode: {snap.device_mode} | Battery: {st.battery_percent}% | "
            f"Slot: {st.slot_index + 1} | "
            f"DPI X: {st.dpi_x} | DPI Y: {st.dpi_y} | "
            f"Poll: {st.polling.hz} Hz | Debounce: {st.debounce_ms} ms | "
            f"Motion Sync: {'on' if st.motion_sync_enabled else 'off'}"
        )
        widget.refresh_from_snapshot(
            True,
            snap.device_mode,
            st,
            self._persisted_lod_level,
            self._persisted_sleep_timeout_seconds,
        )

    def _hydrate_controls_from_status(self, status: object) -> None:
        from incott_configurator.domain.models import HeartbeatStatus

        if not isinstance(status, HeartbeatStatus):
            return

        current_slot_select = self.query_one("#select-current-slot", Select)
        if not self._current_slot_initialized:
            current_slot_select.value = status.slot_index + 1
            self._current_slot_initialized = True
        elif self._current_slot_pending is not None:
            if status.slot_index + 1 == self._current_slot_pending:
                self._current_slot_pending = None
                self._current_slot_dirty = False
            # Keep user-selected value while waiting for device acknowledgement.
        elif self._current_slot_dirty:
            # Keep unsaved user selection.
            pass
        elif current_slot_select.value != status.slot_index + 1:
            current_slot_select.value = status.slot_index + 1

        polling_select = self.query_one("#select-polling", Select)
        if self._polling_pending is not None:
            if status.polling == self._polling_pending:
                self._polling_pending = None
                self._polling_dirty = False
            # Keep user-selected value while waiting for device acknowledgement.
        elif self._polling_dirty:
            # Keep unsaved user selection.
            pass
        elif polling_select.value != int(status.polling):
            polling_select.value = int(status.polling)

        debounce_input = self.query_one("#input-debounce", Input)
        if not debounce_input.has_focus:
            debounce_value = str(status.debounce_ms)
            if debounce_input.value != debounce_value:
                debounce_input.value = debounce_value

        lod_select = self.query_one("#select-lod", Select)
        if self._persisted_lod_level is not None and lod_select.value != self._persisted_lod_level:
            lod_select.value = self._persisted_lod_level

        sleep_input = self.query_one("#input-sleep", Input)
        if not sleep_input.has_focus and self._persisted_sleep_timeout_seconds is not None:
            sleep_value = str(self._persisted_sleep_timeout_seconds)
            if sleep_input.value != sleep_value:
                sleep_input.value = sleep_value

        edit_slot_select = self.query_one("#select-edit-slot", Select)
        edit_slot_value = edit_slot_select.value
        if edit_slot_value is Select.BLANK:
            return

        edit_slot = int(edit_slot_value)  # type: ignore[arg-type]
        if self._dpi_pending is not None:
            pending_slot, pending_x, pending_y = self._dpi_pending
            if (
                status.slot_index + 1 == pending_slot
                and status.dpi_x == pending_x
                and status.dpi_y == pending_y
            ):
                self._dpi_pending = None

        should_hydrate = (
            not self._dpi_edit_dirty
            and self._dpi_pending is None
            and (self._last_hydrated_slot != edit_slot or edit_slot == status.slot_index + 1)
        )
        if should_hydrate:
            self._sync_slot_dpi_inputs(edit_slot)
            self._last_hydrated_slot = edit_slot

    def _sync_slot_dpi_inputs(self, slot: int) -> None:
        dpi_x_input = self.query_one("#input-dpi-x", Input)
        dpi_y_input = self.query_one("#input-dpi-y", Input)
        dpi_x, dpi_y = self._slot_dpi_values[slot]

        if not dpi_x_input.has_focus:
            dpi_x_value = str(dpi_x)
            if dpi_x_input.value != dpi_x_value:
                dpi_x_input.value = dpi_x_value

        if not dpi_y_input.has_focus:
            dpi_y_value = str(dpi_y)
            if dpi_y_input.value != dpi_y_value:
                dpi_y_input.value = dpi_y_value

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-current-slot":
            if event.value is not Select.BLANK:
                self._current_slot_initialized = True
                snapshot = self._session.snapshot()
                if snapshot.status is not None and isinstance(event.value, int):
                    self._current_slot_dirty = (event.value != snapshot.status.slot_index + 1)
                else:
                    self._current_slot_dirty = True
            return

        if event.select.id == "select-polling":
            if event.value is not Select.BLANK:
                snapshot = self._session.snapshot()
                if snapshot.status is not None and isinstance(event.value, int):
                    self._polling_dirty = (event.value != int(snapshot.status.polling))
                else:
                    self._polling_dirty = True
            return

        if event.select.id != "select-edit-slot":
            return

        if event.value is Select.BLANK:
            return

        if not isinstance(event.value, int):
            return

        slot = event.value
        self._sync_slot_dpi_inputs(slot)
        self._last_hydrated_slot = slot
        self._dpi_edit_dirty = False

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in {"input-dpi-x", "input-dpi-y"}:
            self._dpi_edit_dirty = True

    def _apply_switch_slot(self) -> None:
        slot_val = self.query_one("#select-current-slot", Select).value

        if slot_val is Select.BLANK:
            self.notify("Select a current slot first.", title="Error", severity="error")
            return

        try:
            slot = int(slot_val)  # type: ignore[arg-type]
        except (ValueError, TypeError) as exc:
            self.notify(str(exc), title="Validation Error", severity="error")
            return

        self._session.apply_command(build_switch_active_slot(slot - 1))
        self._session.apply_command(build_sync_request())
        self._current_slot_pending = slot
        self._current_slot_dirty = False
        self.notify(f"Switched to slot {slot}", title="Applied", severity="information")

    def _apply_slot_dpi(self) -> None:
        slot_val = self.query_one("#select-edit-slot", Select).value
        dpi_x_str = self.query_one("#input-dpi-x", Input).value
        dpi_y_str = self.query_one("#input-dpi-y", Input).value

        if slot_val is Select.BLANK:
            self.notify("Select a slot to edit first.", title="Error", severity="error")
            return

        try:
            slot = int(slot_val)  # type: ignore[arg-type]
            dpi_x = validate_dpi(int(dpi_x_str))
            dpi_y = validate_dpi(int(dpi_y_str))
        except (ValueError, TypeError) as exc:
            self.notify(str(exc), title="Validation Error", severity="error")
            return

        self._slot_dpi_values[slot] = (dpi_x, dpi_y)
        self._save_local_settings()
        self._dpi_edit_dirty = False
        self._dpi_pending = (slot, dpi_x, dpi_y)

        slot_index_zero_based = slot - 1
        if dpi_x == dpi_y:
            self._session.apply_command(
                build_write_slot_dpi(slot_index_zero_based, dpi_x, axis=AXIS_BOTH)
            )
        else:
            self._session.apply_command(
                build_write_slot_dpi(slot_index_zero_based, dpi_x, axis=AXIS_X)
            )
            self._session.apply_command(
                build_write_slot_dpi(slot_index_zero_based, dpi_y, axis=AXIS_Y)
            )

        self._session.apply_command(build_sync_request())

        self.notify(
            f"Stored DPI for slot {slot}: X={dpi_x} Y={dpi_y}",
            title="Slot DPI Saved",
            severity="information",
        )

    def _apply_polling(self) -> None:
        raw = self.query_one("#select-polling", Select).value

        if raw is Select.BLANK:
            self.notify("Select a polling rate.", title="Error", severity="error")
            return

        try:
            polling = PollingRate(int(raw))  # type: ignore[arg-type]
        except (ValueError, TypeError) as exc:
            self.notify(str(exc), title="Error", severity="error")
            return

        self._session.apply_command(build_set_polling_rate(polling))
        self._session.apply_command(build_sync_request())
        self._polling_pending = polling
        self._polling_dirty = False
        self.notify(f"{polling.hz} Hz", title="Polling Rate Applied", severity="information")

    def _apply_hardware(self) -> None:
        errors: list[str] = []
        should_persist_local_settings = False
        any_command_sent = False

        try:
            debounce = validate_debounce_ms(int(self.query_one("#input-debounce", Input).value))
            self._session.apply_command(build_set_debounce_ms(debounce))
            any_command_sent = True
        except (ValueError, TypeError) as exc:
            errors.append(f"Debounce: {exc}")

        lod_raw = self.query_one("#select-lod", Select).value
        if lod_raw is not Select.BLANK:
            try:
                lod_level = LodLevel(int(lod_raw))  # type: ignore[arg-type]
                self._persisted_lod_level = int(lod_level)
                should_persist_local_settings = True
                self._session.apply_command(build_set_lod(lod_level))
                any_command_sent = True
            except (ValueError, TypeError) as exc:
                errors.append(f"LOD: {exc}")

        try:
            sleep_s = validate_sleep_seconds(int(self.query_one("#input-sleep", Input).value))
            self._persisted_sleep_timeout_seconds = sleep_s
            should_persist_local_settings = True
            self._session.apply_command(build_set_sleep_timeout(sleep_s))
            any_command_sent = True
        except (ValueError, TypeError) as exc:
            errors.append(f"Sleep: {exc}")

        if any_command_sent:
            self._session.apply_command(build_sync_request())

        if should_persist_local_settings:
            self._save_local_settings()

        if errors:
            self.notify("\n".join(errors), title="Errors", severity="error")
        else:
            self.notify("Hardware settings applied.", title="Applied", severity="information")

    def _save_local_settings(self) -> None:
        self._settings_store.save(
            LocalSettingsState(
                slot_dpi_values=self._slot_dpi_values,
                lod_level=self._persisted_lod_level,
                sleep_timeout_seconds=self._persisted_sleep_timeout_seconds,
            )
        )
