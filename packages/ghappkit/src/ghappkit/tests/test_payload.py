"""Tests for JSON payload parsing."""

from __future__ import annotations

import json

import pytest

from ghappkit.exceptions import PayloadParseError
from ghappkit.payload import parse_json_payload


def test_valid_object() -> None:
    assert parse_json_payload(b'{"a":1}') == {"a": 1}


def test_invalid_json() -> None:
    with pytest.raises(PayloadParseError, match="valid JSON"):
        parse_json_payload(b"{")


def test_non_object_json() -> None:
    with pytest.raises(PayloadParseError, match="object"):
        parse_json_payload(json.dumps([1]).encode("utf-8"))
