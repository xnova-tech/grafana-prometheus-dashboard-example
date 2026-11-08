"""FastAPI assembly and HTTP instrumentation middleware."""

from time import perf_counter

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from grafana_demo.config import Settings
from grafana_demo.metrics import HttpMetrics, normalize_route
from grafana_demo.routes import create_router


def create_app(
    settings: Settings | None = None,
    metrics: HttpMetrics | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    app_metrics = metrics or HttpMetrics.create()
    application = FastAPI(title="Grafana metrics demo", docs_url=None, redoc_url=None)

    @application.middleware("http")
    async def record_http_metrics(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            app_metrics.observe(
                route=normalize_route(request.url.path),
                status=status_code,
                duration_seconds=perf_counter() - started,
            )

    application.include_router(create_router(app_settings, app_metrics))
    return application
