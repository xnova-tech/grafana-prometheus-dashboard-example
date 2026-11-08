"""Deterministic request sequences used by the load CLI and tests."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic, sleep
from typing import Final

import httpx


class Profile(StrEnum):
    BASELINE = "baseline"
    ERRORS = "errors"
    SLOW = "slow"
    RECOVERY = "recovery"


PROFILE_PATHS: Final[dict[Profile, tuple[str, ...]]] = {
    Profile.BASELINE: ("/",),
    Profile.ERRORS: ("/", "/", "/", "/error"),
    Profile.SLOW: ("/", "/", "/slow"),
    Profile.RECOVERY: ("/",),
}
EXPECTED_STATUS: Final = {"/": 200, "/error": 503, "/slow": 200}


class LoadFailure(RuntimeError):
    """The target did not satisfy the selected profile contract."""


@dataclass(frozen=True, slots=True)
class LoadConfig:
    profile: Profile
    seconds: int = 75
    requests_per_second: int = 6
    base_url: str = "http://127.0.0.1:8000"

    def __post_init__(self) -> None:
        if self.seconds <= 0:
            raise ValueError("seconds must be positive")
        if not 1 <= self.requests_per_second <= 20:
            raise ValueError("requests per second must be between 1 and 20")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("base URL must use HTTP or HTTPS")

    @property
    def request_count(self) -> int:
        return self.seconds * self.requests_per_second


@dataclass(frozen=True, slots=True)
class LoadResult:
    profile: Profile
    requests: int
    statuses: dict[int, int]

    def render(self) -> str:
        counts = ", ".join(f"http_{code}={self.statuses[code]}" for code in sorted(self.statuses))
        return f"mode={self.profile} requests={self.requests} {counts}"


def run_profile(
    config: LoadConfig,
    client: httpx.Client,
    *,
    clock: Callable[[], float] = monotonic,
    sleeper: Callable[[float], None] = sleep,
) -> LoadResult:
    paths = PROFILE_PATHS[config.profile]
    statuses: Counter[int] = Counter()
    started = clock()
    for sequence in range(config.request_count):
        path = paths[sequence % len(paths)]
        try:
            response = client.get(path)
        except httpx.HTTPError as error:
            raise LoadFailure(f"{path}: request failed: {error}") from error
        expected = EXPECTED_STATUS[path]
        if response.status_code != expected:
            raise LoadFailure(f"{path}: expected {expected}, got {response.status_code}")
        statuses[response.status_code] += 1
        deadline = started + (sequence + 1) / config.requests_per_second
        remaining = deadline - clock()
        if remaining > 0:
            sleeper(remaining)
    return LoadResult(config.profile, config.request_count, dict(statuses))
