"""Run the demo API with Uvicorn."""

import uvicorn

from grafana_demo.app import create_app
from grafana_demo.config import Settings


def main() -> None:
    settings = Settings.from_environment()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
