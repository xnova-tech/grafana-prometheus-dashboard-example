"""Stable HTTP and metrics observation used by publication verification."""

import asyncio

from httpx import ASGITransport, AsyncClient

from grafana_demo import Settings, create_app


async def observe() -> None:
    app = create_app(Settings(slow_delay_seconds=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        observations = [("/", 200), ("/error", 503), ("/slow", 200), ("/missing", 404)]
        for path, expected in observations:
            response = await client.get(path)
            if response.status_code != expected:
                raise AssertionError(f"{path}: expected {expected}, got {response.status_code}")
        metrics = await client.get("/metrics")
        repeated = await client.get("/metrics")
        if metrics.content != repeated.content:
            raise AssertionError("metrics scrape changed application metrics")
        body = metrics.text
        required = (
            'demo_http_requests_total{route="/",status="200"} 1.0',
            'demo_http_requests_total{route="/error",status="503"} 1.0',
            'demo_http_requests_total{route="/slow",status="200"} 1.0',
            'demo_http_requests_total{route="other",status="404"} 1.0',
            'demo_http_request_duration_seconds_count{route="/slow"} 1.0',
        )
        if any(sample not in body for sample in required):
            raise AssertionError("expected counter or histogram sample is missing")
    print("http: 200=ok 404=ok 503=ok slow=ok")
    print("metrics: counters=4 histogram=observed scrape_excluded=true")


if __name__ == "__main__":
    asyncio.run(observe())
