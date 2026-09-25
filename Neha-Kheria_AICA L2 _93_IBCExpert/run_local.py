"""Development/source launcher. The production desktop wrapper is a later packaging milestone."""
from __future__ import annotations

from app.core.config import AppConfig
from app.web import create_app


def main() -> None:
    import uvicorn

    config = AppConfig()
    if config.host != "127.0.0.1":
        raise RuntimeError("Refusing non-loopback binding.")
    # Fixed localhost port for source runs. Packaged desktop wrapper will reserve a free loopback port.
    uvicorn.run(create_app(config=config), host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
