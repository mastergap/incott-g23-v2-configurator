# incott-g23-v2-configurator

Cross-platform offline configurator for the Incott G23 V2 mouse.

This project started from protocol reverse engineering and now includes a production TUI application to read and configure mouse settings without the vendor web app.

## Introduction

The repository contains two tracks:

- Reverse engineering artifacts and protocol notes in `reverse-engineering/`.
- Production application code in `src/incott_configurator/`.

The goal is to provide a reliable, maintainable desktop configuration tool with real-time status updates and safe write commands.

## Technical Stack

### Language

- Python 3.12+

### UI

- Textual (terminal user interface)

### HID / Device Communication

- `hidapi` (Python bindings)

### Quality and Tooling

- `pytest` for tests
- `mypy` (strict type checking)
- `ruff` (linting)

### Packaging

- Python package via `pyproject.toml`
- Binary packaging with PyInstaller (recommended)

## Project Architecture

The production app is layered for maintainability:

- `src/incott_configurator/domain/`
: typed models, enums, and validation logic.
- `src/incott_configurator/protocol/`
: HID packet parsing and command builders.
- `src/incott_configurator/transport/`
: transport abstraction and hidapi adapter.
- `src/incott_configurator/service/`
: session loop, command queue, local settings persistence.
- `src/incott_configurator/app/`
: Textual TUI screens/widgets.
- `tests/`
: unit tests for parsing, encoding, and validation.

## Implemented Features

### Real-Time Monitoring

- Live heartbeat parsing (Report ID `0x09`).
- Always-visible current settings panel.
- Connection mode detection (wired/wireless).
- Battery, active slot, DPI X/Y, polling, debounce, motion sync display.

### Configuration Commands

- Active slot switching.
- Per-slot DPI customization.
- Polling rate configuration.
- Debounce configuration.
- LOD configuration.
- Sleep timeout configuration.

### Persistence and UX Behavior

- Local persistence for slot DPI values, LOD, and sleep timeout.
- Pending/dirty UI state to avoid refresh overwriting unsaved selections.
- Sync request dispatch after writes to refresh current settings quickly.

## Install and Run

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the app with dev dependencies

```bash
pip install -e .[dev]
```

### 3. Run tests and checks (recommended)

```bash
pytest
mypy src
ruff check src tests
```

### 4. Start the app

```bash
incott-configurator
```

Alternative:

```bash
python -m incott_configurator.main
```

## Build a Binary

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build

```bash
pyinstaller \
  --name incott-configurator \
  --onefile \
  --collect-all textual \
  --hidden-import hid \
  -m incott_configurator.main
```

Output binary is created in `dist/`.

## Distribution Notes

### Linux

- Distribute the binary from `dist/incott-configurator`.
- Users may need udev permissions for hidraw access.

### macOS

- Build on macOS to get a native binary.
- For public distribution, codesign and notarize the binary/app.

### Windows

- Build on Windows to get a native `.exe`.
- Ship `dist/incott-configurator.exe`.
- Code signing is recommended for trust and SmartScreen behavior.

## Current Scope and Limitations

- Reverse engineering is still evolving for undocumented features (for example performance modes).
- Documented protocol paths are implemented; future protocol discoveries will be integrated incrementally.

## Notes

- Reverse-engineering scripts are reference/test-vector material only.
- Production code does not import runtime logic from reverse-engineering scripts.
