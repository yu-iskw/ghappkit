"""JWT creation tests."""

from __future__ import annotations

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ghappkit_client.auth import create_app_jwt


def test_app_jwt_roundtrip() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    token = create_app_jwt(424242, pem, ttl_seconds=120)
    public_key = key.public_key()
    decoded = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )
    assert int(decoded["iss"]) == 424242
