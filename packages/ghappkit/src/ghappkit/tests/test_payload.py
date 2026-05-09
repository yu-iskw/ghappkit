"""Tests for JSON payload parsing."""

from __future__ import annotations

import json

import pytest

from ghappkit.exceptions import PayloadParseError
from ghappkit.payload import parse_json_payload


def test_valid_object() -> None:
    payload = parse_json_payload(b'{"a":1}')
    assert payload == {"a": 1}
    assert parse_json_payload(json.dumps({"a": 1}).encode("utf-8")) == {"a": 1}


def test_invalid_json() -> None:
    with pytest.raises(PayloadParseError, match="valid JSON") as ctx:
        parse_json_payload(b"{")
    assert ctx.value.kind == "json"


def test_non_object_json() -> None:
    with pytest.raises(PayloadParseError, match="object") as ctx:
        parse_json_payload(json.dumps([1]).encode("utf-8"))
    assert ctx.value.kind == "not_object"


def test_non_utf8_body() -> None:
    with pytest.raises(PayloadParseError, match="utf-8") as ctx:
        parse_json_payload(b"\xff\xfe")
    assert ctx.value.kind == "utf8"
