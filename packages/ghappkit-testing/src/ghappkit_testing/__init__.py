"""Testing utilities for ghappkit applications."""

from ghappkit.parsing import split_qualified_event

from ghappkit_testing.fake_client import FakeGitHubClient
from ghappkit_testing.fixtures import FIXTURES, payload_fixture
from ghappkit_testing.signatures import sign_sha256_payload
from ghappkit_testing.simulator import GhappkitTestClient, OctoflowTestClient
from ghappkit_testing.test_settings import make_test_settings

# RFC snippet compatibility — prefer ``make_test_settings``.
test_settings = make_test_settings

__all__ = [
    "FIXTURES",
    "FakeGitHubClient",
    "GhappkitTestClient",
    "OctoflowTestClient",
    "make_test_settings",
    "payload_fixture",
    "sign_sha256_payload",
    "split_qualified_event",
    "test_settings",
]
