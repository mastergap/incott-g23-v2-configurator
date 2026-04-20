"""Application entrypoint."""

from __future__ import annotations

from incott_configurator.app.tui import IncottConfiguratorApp
from incott_configurator.service.session import SessionManager
from incott_configurator.transport.hidapi_adapter import HidApiAdapter


def main() -> None:
    transport = HidApiAdapter()
    session = SessionManager(transport=transport)
    session.start()
    try:
        app = IncottConfiguratorApp(session)
        app.run()
    finally:
        session.stop()


if __name__ == "__main__":
    main()
