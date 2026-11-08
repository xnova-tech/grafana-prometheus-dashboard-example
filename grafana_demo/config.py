"""Environment-backed settings for the demo API."""

from dataclasses import dataclass
from os import environ


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    slow_delay_seconds: float = 0.35

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("host must not be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not 0 <= self.slow_delay_seconds <= 5:
            raise ValueError("slow delay must be between 0 and 5 seconds")

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            host=environ.get("DEMO_HOST", "0.0.0.0"),
            port=int(environ.get("DEMO_PORT", "8000")),
            slow_delay_seconds=float(environ.get("DEMO_SLOW_DELAY_SECONDS", "0.35")),
        )
