from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pyrate_limiter import Limiter, Rate


class ProviderRateLimitExceeded(Exception):
    """Raised when a provider request cannot acquire a rate-limit permit."""


WaitStrategy = Literal["wait", "fail_fast"]


@dataclass(frozen=True)
class ProviderRateLimitConfig:
    max_requests: int
    window_seconds: float
    wait_strategy: WaitStrategy = "wait"
    timeout_seconds: float | None = None


class ProviderRateLimiter:
    def __init__(self, configs: dict[str, ProviderRateLimitConfig]) -> None:
        self._configs = dict(configs)
        self._limiters = {
            provider: Limiter(
                Rate(config.max_requests, int(config.window_seconds * 1000))
            )
            for provider, config in self._configs.items()
        }

    def acquire(self, provider_name: str) -> None:
        config = self._configs.get(provider_name)
        limiter = self._limiters.get(provider_name)
        if config is None or limiter is None:
            return
        acquired = limiter.try_acquire(
            provider_name,
            blocking=config.wait_strategy == "wait",
            timeout=(
                config.timeout_seconds if config.timeout_seconds is not None else -1
            ),
        )
        if acquired is False:
            msg = f"rate limit exceeded for provider {provider_name}"
            raise ProviderRateLimitExceeded(msg)
