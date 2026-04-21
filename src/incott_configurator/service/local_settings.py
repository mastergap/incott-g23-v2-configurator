"""Local persistence for settings that are not fully exposed by heartbeat reports."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LocalSettingsState:
    slot_dpi_values: dict[int, tuple[int, int]]
    lod_level: int | None = None
    sleep_timeout_seconds: int | None = None


class LocalSettingsStore:
    def __init__(self, app_name: str = "incott-g23-v2-configurator") -> None:
        self._app_name = app_name
        self._path = self._resolve_path(app_name)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> LocalSettingsState:
        if not self._path.exists():
            return LocalSettingsState(slot_dpi_values={})

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return LocalSettingsState(slot_dpi_values={})

        slot_values_raw = raw.get("slot_dpi_values", {})
        slot_dpi_values: dict[int, tuple[int, int]] = {}
        if isinstance(slot_values_raw, dict):
            for key, value in slot_values_raw.items():
                if not isinstance(key, str) or not key.isdigit():
                    continue
                if not isinstance(value, list | tuple) or len(value) != 2:
                    continue
                x_value, y_value = value
                if not isinstance(x_value, int) or not isinstance(y_value, int):
                    continue
                slot_dpi_values[int(key)] = (x_value, y_value)

        lod_level = raw.get("lod_level")
        if not isinstance(lod_level, int):
            lod_level = None

        sleep_timeout_seconds = raw.get("sleep_timeout_seconds")
        if not isinstance(sleep_timeout_seconds, int):
            sleep_timeout_seconds = None

        return LocalSettingsState(
            slot_dpi_values=slot_dpi_values,
            lod_level=lod_level,
            sleep_timeout_seconds=sleep_timeout_seconds,
        )

    def save(self, state: LocalSettingsState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "slot_dpi_values": {
                str(slot): [values[0], values[1]]
                for slot, values in sorted(state.slot_dpi_values.items())
            },
            "lod_level": state.lod_level,
            "sleep_timeout_seconds": state.sleep_timeout_seconds,
        }
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _resolve_path(self, app_name: str) -> Path:
        if sys.platform == "darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        elif os.name == "nt":
            appdata = os.environ.get("APPDATA")
            base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        else:
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            base_dir = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"

        return base_dir / app_name / "settings.json"