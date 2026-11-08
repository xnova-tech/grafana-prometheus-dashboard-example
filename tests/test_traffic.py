"""Deterministic load-profile contracts."""

from collections.abc import Callable

import httpx
import pytest

from grafana_demo.traffic import LoadConfig, LoadFailure, Profile, run_profile


def client_for(status_for_path: Callable[[str], int]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_for_path(request.url.path), request=request)

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="http://test")


@pytest.mark.parametrize(
    ("profile", "statuses"),
    [
        (Profile.BASELINE, {200: 8}),
        (Profile.ERRORS, {200: 6, 503: 2}),
        (Profile.SLOW, {200: 8}),
        (Profile.RECOVERY, {200: 8}),
    ],
)
def test_profiles_send_exact_request_count(profile: Profile, statuses: dict[int, int]) -> None:
    expected = {"/": 200, "/error": 503, "/slow": 200}
    with client_for(expected.__getitem__) as client:
        result = run_profile(
            LoadConfig(profile, seconds=2, requests_per_second=4),
            client,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )

    assert result.requests == 8
    assert result.statuses == statuses


def test_error_profile_has_stable_sequence() -> None:
    paths: list[str] = []

    def status(path: str) -> int:
        paths.append(path)
        return 503 if path == "/error" else 200

    with client_for(status) as client:
        run_profile(
            LoadConfig(Profile.ERRORS, seconds=2, requests_per_second=4),
            client,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )

    assert paths == ["/", "/", "/", "/error", "/", "/", "/", "/error"]


def test_unexpected_status_fails_profile() -> None:
    with client_for(lambda _path: 500) as client, pytest.raises(LoadFailure, match="expected 200, got 500"):
        run_profile(
            LoadConfig(Profile.BASELINE, seconds=1, requests_per_second=1),
            client,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )


@pytest.mark.parametrize(
    "config",
    [
        lambda: LoadConfig(Profile.BASELINE, seconds=0),
        lambda: LoadConfig(Profile.BASELINE, requests_per_second=21),
        lambda: LoadConfig(Profile.BASELINE, base_url="ftp://invalid"),
    ],
)
def test_invalid_load_config_is_rejected(config: Callable[[], LoadConfig]) -> None:
    with pytest.raises(ValueError):
        config()
