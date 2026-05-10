"""GitHub webhook JSON payload parsing."""

from __future__ import annotations

import json
from typing import Any

from ghappkit.exceptions import PayloadParseError


def parse_json_payload(body: bytes) -> dict[str, Any]:
    """Parse JSON object payloads."""
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadParseError("payload must be utf-8") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadParseError("payload is not valid JSON") from exc
    if not isinstance(data, dict):
        raise PayloadParseError("payload JSON must be an object")
    return data
