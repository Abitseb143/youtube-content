import base64
import time

import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient, Response

from faceless.auth.clerk import _jwks_cache_clear
from faceless.main import create_app


@pytest.fixture
def signing_setup():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_nums = key.public_key().public_numbers()

    def b64(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    jwk = {
        "kid": "kid-test",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": b64(pub_nums.n),
        "e": b64(pub_nums.e),
    }
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return priv_pem, jwk


def _make_token(priv_pem: bytes, *, sub: str, email: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "iss": "https://test.clerk.accounts.dev",
            "aud": "https://app.test",
            "iat": now,
            "exp": now + 60,
            "email": email,
        },
        priv_pem,
        algorithm="RS256",
        headers={"kid": "kid-test"},
    )


@pytest.mark.asyncio
async def test_me_creates_and_returns_user(db_engine, signing_setup):
    priv, jwk = signing_setup
    _jwks_cache_clear()
    app = create_app()

    with respx.mock(assert_all_called=False):
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = _make_token(priv, sub="user_first", email="first@example.com")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/me", headers={"authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["email"] == "first@example.com"
            assert body["credit_balance"] == 0
            first_id = body["id"]

            # Same Clerk sub → same user
            resp2 = await client.get("/api/v1/me", headers={"authorization": f"Bearer {token}"})
            assert resp2.json()["id"] == first_id


@pytest.mark.asyncio
async def test_me_rejects_missing_token():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_me_rejects_invalid_token():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/me", headers={"authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401
