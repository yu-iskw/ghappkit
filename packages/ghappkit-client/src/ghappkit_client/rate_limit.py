"""GitHub rate-limit metadata from response headers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitInfo:
    """Subset of X-RateLimit-* headers."""

    limit: int | None
    remaining: int | None
    reset_epoch: int | None


def parse_rate_limit(headers: Mapping[str, str]) -> RateLimitInfo:
    """Parse GitHub rate limit headers (case-insensitive keys)."""
    lowered = {k.lower(): v for k, v in headers.items()}
    return RateLimitInfo(
        limit=_parse_int(lowered.get("x-ratelimit-limit")),
        remaining=_parse_int(lowered.get("x-ratelimit-remaining")),
        reset_epoch=_parse_int(lowered.get("x-ratelimit-reset")),
    )


def _parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
