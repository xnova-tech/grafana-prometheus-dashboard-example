"""Prometheus instruments owned by one application instance."""

from dataclasses import dataclass
from typing import Final

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

KNOWN_ROUTES: Final = frozenset({"/", "/error", "/slow"})
INITIAL_SERIES: Final = (
    ("/", "200"),
    ("/error", "503"),
    ("/slow", "200"),
    ("other", "404"),
)
HISTOGRAM_BUCKETS: Final = (0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0)


def normalize_route(path: str) -> str:
    return path if path in KNOWN_ROUTES else "other"


@dataclass(frozen=True, slots=True)
class HttpMetrics:
    registry: CollectorRegistry
    requests: Counter
    duration: Histogram

    @classmethod
    def create(cls) -> "HttpMetrics":
        registry = CollectorRegistry()
        requests = Counter(
            "demo_http_requests",
            "HTTP requests received by the demo API.",
            ("route", "status"),
            registry=registry,
        )
        duration = Histogram(
            "demo_http_request_duration_seconds",
            "HTTP response duration of the demo API in seconds.",
            ("route",),
            buckets=HISTOGRAM_BUCKETS,
            registry=registry,
        )
        for route, status in INITIAL_SERIES:
            requests.labels(route=route, status=status)
        return cls(registry=registry, requests=requests, duration=duration)

    def observe(self, *, route: str, status: int, duration_seconds: float) -> None:
        self.requests.labels(route=route, status=str(status)).inc()
        self.duration.labels(route=route).observe(duration_seconds)

    def exposition(self) -> bytes:
        return generate_latest(self.registry)
