"""FastAPI service and deterministic traffic profiles for the Grafana example."""

from grafana_demo.app import create_app
from grafana_demo.config import Settings

__all__ = ["Settings", "create_app"]
