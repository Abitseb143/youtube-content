"""Clerk JWT verification via the public JWKS endpoint.

Tokens are RS256-signed; public keys are fetched from
`{issuer}/.well-known/jwks.json` and cached in-process for 10 minutes.
"""

import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from faceless.config import get_settings


class InvalidToken(Exception):
    """Raised when the JWT is malformed, expired, has wrong audience, or fails signature."""


@dataclass(frozen=True)
class ClerkClaims:
    sub: str  # Clerk user id
    email: str | None
    raw: dict[str, Any]


_JWKS_TTL_S = 600
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _jwks_cache_clear() -> None:
    """Test helper — clear the JWKS cache."""
    _jwks_cache.clear()


async def _fetch_jwks(issuer: str) -> dict[str, Any]:
    cached = _jwks_cache.get(issuer)
    if cached and cached[0] > time.time():
        return cached[1]
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{issuer.rstrip('/')}/.well-known/jwks.json")
        resp.raise_for_status()
        jwks = resp.json()
    _jwks_cache[issuer] = (time.time() + _JWKS_TTL_S, jwks)
    return jwks


def _key_for_kid(jwks: dict[str, Any], kid: str):
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key)
    raise InvalidToken(f"unknown kid: {kid}")


async def verify_clerk_token(token: str) -> ClerkClaims:
    settings = get_settings()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise InvalidToken("malformed token") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise InvalidToken("missing kid")

    jwks = await _fetch_jwks(settings.clerk_jwt_issuer)
    public_key = _key_for_kid(jwks, kid)

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.clerk_jwt_audience,
            issuer=settings.clerk_jwt_issuer,
        )
    except jwt.ExpiredSignatureError as e:
        raise InvalidToken("expired") from e
    except jwt.InvalidTokenError as e:
        raise InvalidToken(str(e)) from e

    sub = claims.get("sub")
    if not sub:
        raise InvalidToken("missing sub claim")

    return ClerkClaims(sub=sub, email=claims.get("email"), raw=claims)
