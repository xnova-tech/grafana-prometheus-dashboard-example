"""HTTP and Prometheus instrumentation contracts."""

import re

import pytest
from httpx import ASGITransport, AsyncClient

from grafana_demo import Settings, create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    app = create_app(Settings(slow_delay_seconds=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client


def sample_value(body: str, metric: str, labels: str) -> float:
    match = re.search(
        rf"^{re.escape(metric)}\{{{re.escape(labels)}\}}\s+([0-9.eE+-]+)$",
        body,
        flags=re.MULTILINE,
    )
    if match is None:
        raise AssertionError(f"missing sample {metric}{{{labels}}}")
    return float(match.group(1))


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "status", "body"),
    [
        ("/", 200, "demo: ok\n"),
        ("/error", 503, "demo: controlled error\n"),
        ("/slow", 200, "demo: slow\n"),
        ("/missing", 404, '{"detail":"Not Found"}'),
    ],
)
async def test_routes_return_controlled_responses(
    client: AsyncClient,
    path: str,
    status: int,
    body: str,
) -> None:
    response = await client.get(path)

    assert response.status_code == status
    assert response.text == body


@pytest.mark.anyio
async def test_requests_increment_bounded_counter_labels(client: AsyncClient) -> None:
    for path in ("/", "/error", "/slow", "/unknown"):
        await client.get(path)

    body = (await client.get("/metrics")).text

    assert sample_value(body, "demo_http_requests_total", 'route="/",status="200"') == 1
    assert sample_value(body, "demo_http_requests_total", 'route="/error",status="503"') == 1
    assert sample_value(body, "demo_http_requests_total", 'route="/slow",status="200"') == 1
    assert sample_value(body, "demo_http_requests_total", 'route="other",status="404"') == 1
    assert 'route="/unknown"' not in body


@pytest.mark.anyio
async def test_histogram_observes_slow_route_and_expected_bucket(client: AsyncClient) -> None:
    await client.get("/slow")

    body = (await client.get("/metrics")).text

    assert sample_value(body, "demo_http_request_duration_seconds_count", 'route="/slow"') == 1
    assert (
        sample_value(
            body,
            "demo_http_request_duration_seconds_bucket",
            'le="0.5",route="/slow"',
        )
        == 1
    )


@pytest.mark.anyio
async def test_metrics_scrape_has_no_application_side_effect(client: AsyncClient) -> None:
    first = await client.get("/metrics")
    second = await client.get("/metrics")

    assert first.status_code == 200
    assert first.content == second.content
    assert 'route="/metrics"' not in first.text


def test_invalid_settings_are_rejected() -> None:
    with pytest.raises(ValueError, match="port"):
        Settings(port=0)
    with pytest.raises(ValueError, match="slow delay"):
        Settings(slow_delay_seconds=-1)


def test_environment_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_HOST", "127.0.0.1")
    monkeypatch.setenv("DEMO_PORT", "9000")
    monkeypatch.setenv("DEMO_SLOW_DELAY_SECONDS", "0.1")

    settings = Settings.from_environment()

    assert settings == Settings(host="127.0.0.1", port=9000, slow_delay_seconds=0.1)
