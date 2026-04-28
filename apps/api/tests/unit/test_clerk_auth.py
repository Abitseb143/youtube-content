import base64
import time

import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import Response

from faceless.auth.clerk import (
    ClerkClaims,
    InvalidToken,
    _jwks_cache_clear,
    verify_clerk_token,
)


@pytest.fixture
def rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = key.public_key()
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    nums = pub.public_numbers()

    def b64(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    jwk = {
        "kid": "test-kid",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": b64(nums.n),
        "e": b64(nums.e),
    }
    return priv_pem, jwk


def make_token(
    priv_pem: bytes,
    *,
    sub: str = "user_x",
    iss: str = "https://test.clerk.accounts.dev",
    aud: str = "https://app.test",
    exp_offset: int = 60,
    kid: str = "test-kid",
) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "iss": iss, "aud": aud, "iat": now, "exp": now + exp_offset, "email": "x@y.com"},
        priv_pem,
        algorithm="RS256",
        headers={"kid": kid},
    )


@pytest.mark.asyncio
async def test_verify_valid_token(rsa_keypair):
    priv, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv)
        claims = await verify_clerk_token(token)
        assert isinstance(claims, ClerkClaims)
        assert claims.sub == "user_x"
        assert claims.email == "x@y.com"


@pytest.mark.asyncio
async def test_expired_token_rejected(rsa_keypair):
    priv, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv, exp_offset=-10)
        with pytest.raises(InvalidToken):
            await verify_clerk_token(token)


@pytest.mark.asyncio
async def test_wrong_audience_rejected(rsa_keypair):
    priv, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv, aud="https://wrong.example.com")
        with pytest.raises(InvalidToken):
            await verify_clerk_token(token)


@pytest.mark.asyncio
async def test_unknown_kid_rejected(rsa_keypair):
    priv, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv, kid="unknown-kid")
        with pytest.raises(InvalidToken):
            await verify_clerk_token(token)
