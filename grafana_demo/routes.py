"""HTTP routes for controlled success, error, latency and metrics responses."""

import asyncio

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.responses import PlainTextResponse

from grafana_demo.config import Settings
from grafana_demo.metrics import HttpMetrics


def create_router(settings: Settings, metrics: HttpMetrics) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=PlainTextResponse)
    async def home() -> str:
        return "demo: ok\n"

    @router.get("/error", response_class=PlainTextResponse)
    async def controlled_error() -> Response:
        return PlainTextResponse("demo: controlled error\n", status_code=503)

    @router.get("/slow", response_class=PlainTextResponse)
    async def controlled_latency() -> str:
        await asyncio.sleep(settings.slow_delay_seconds)
        return "demo: slow\n"

    @router.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> Response:
        return Response(content=metrics.exposition(), headers={"Content-Type": CONTENT_TYPE_LATEST})

    return router
