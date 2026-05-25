"""
Supabase JWT verifier with JWKS caching.

Supabase signs session tokens with ES256 (ECC P-256). The signing key
rotates via the JWT Keys panel — Current → Standby → Promoted → Previous.
Public keys are exposed at /auth/v1/.well-known/jwks.json.

This module:
  - Fetches and caches the JWKS in-memory with a TTL (default 15 min)
  - Verifies tokens by matching the JWT header's `kid` to a cached key
  - On unknown `kid`, refreshes JWKS once before failing (handles rotation)
  - Validates signature, exp, iss, aud per Supabase's claims contract
  - Is safe to share across concurrent requests (asyncio.Lock guards refresh)

Usage:
    verifier = SupabaseJWTVerifier(
        project_url="https://zrcrrtrvyldzaqukwzge.supabase.co",
    )
    claims = await verifier.verify(token)
    user_id = claims["sub"]

Dependencies (add to requirements.txt):
    PyJWT[crypto]>=2.8.0
    httpx>=0.25.0
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import PyJWK, PyJWKSet
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    PyJWTError,
)


# ============================================================================
# Exceptions
# ============================================================================


class JWTVerificationError(Exception):
    """Base class. Map to HTTP 401 at the FastAPI dependency layer."""


class JWTExpiredError(JWTVerificationError):
    """Token's `exp` claim is in the past."""


class JWTSignatureError(JWTVerificationError):
    """Signature could not be verified against any known JWKS key."""


class JWTClaimsError(JWTVerificationError):
    """Signature valid, but `iss`/`aud`/required-claim check failed."""


class JWKSUnavailableError(JWTVerificationError):
    """JWKS endpoint unreachable on a fresh fetch with no usable cache."""


# ============================================================================
# Verifier
# ============================================================================


@dataclass
class _CachedJWKS:
    jwks: PyJWKSet
    fetched_at: float


class SupabaseJWTVerifier:
    """One instance per FastAPI app. Holds JWKS cache, verifies tokens."""

    EXPECTED_ALGORITHMS = ["ES256"]
    EXPECTED_AUDIENCE = "authenticated"
    REQUIRED_CLAIMS = ["exp", "iat", "sub"]

    def __init__(
        self,
        project_url: str,
        cache_ttl_seconds: int = 900,
        http_timeout_seconds: float = 5.0,
    ) -> None:
        self._project_url = project_url.rstrip("/")
        self._jwks_url = f"{self._project_url}/auth/v1/.well-known/jwks.json"
        self._issuer = f"{self._project_url}/auth/v1"
        self._cache_ttl = cache_ttl_seconds
        self._http_timeout = http_timeout_seconds
        self._cache: _CachedJWKS | None = None
        self._lock = asyncio.Lock()

    async def verify(self, token: str) -> dict[str, Any]:
        """
        Verify a Supabase JWT and return its decoded claims.

        Raises:
            JWTSignatureError: malformed token, missing kid, no matching key,
                or signature mismatch.
            JWTExpiredError:   token past `exp`.
            JWTClaimsError:    iss/aud/required-claim check failed.
            JWKSUnavailableError: JWKS endpoint unreachable, no cache fallback.
        """
        try:
            unverified_header = jwt.get_unverified_header(token)
        except PyJWTError as e:
            raise JWTSignatureError(f"Malformed token header: {e}") from e

        kid = unverified_header.get("kid")
        if not kid:
            raise JWTSignatureError("Token header missing 'kid'")

        # First pass: try cached JWKS
        signing_key = await self._get_key(kid, force_refresh=False)
        # Second pass: force refresh on miss (handles key rotation)
        if signing_key is None:
            signing_key = await self._get_key(kid, force_refresh=True)
        if signing_key is None:
            raise JWTSignatureError(
                f"No JWKS key matches kid={kid!r} (refreshed once)"
            )

        try:
            claims = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=self.EXPECTED_ALGORITHMS,
                audience=self.EXPECTED_AUDIENCE,
                issuer=self._issuer,
                options={"require": self.REQUIRED_CLAIMS},
            )
        except ExpiredSignatureError as e:
            raise JWTExpiredError("Token expired") from e
        except (InvalidAudienceError, InvalidIssuerError) as e:
            raise JWTClaimsError(f"Invalid claims: {e}") from e
        except InvalidTokenError as e:
            raise JWTSignatureError(f"Invalid token: {e}") from e

        return claims

    # ------------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------------

    async def _get_key(self, kid: str, *, force_refresh: bool) -> PyJWK | None:
        jwks = await self._get_jwks(force_refresh=force_refresh)
        for key in jwks.keys:
            if key.key_id == kid:
                return key
        return None

    async def _get_jwks(self, *, force_refresh: bool) -> PyJWKSet:
        now = time.monotonic()
        if (
            not force_refresh
            and self._cache is not None
            and now - self._cache.fetched_at < self._cache_ttl
        ):
            return self._cache.jwks

        async with self._lock:
            # Re-check under lock — another coroutine may have just refreshed
            now = time.monotonic()
            if (
                not force_refresh
                and self._cache is not None
                and now - self._cache.fetched_at < self._cache_ttl
            ):
                return self._cache.jwks

            try:
                async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                    response = await client.get(self._jwks_url)
                    response.raise_for_status()
                    jwks_data = response.json()
            except httpx.HTTPError as e:
                # Prefer stale cache over a hard failure during a refresh
                if self._cache is not None:
                    return self._cache.jwks
                raise JWKSUnavailableError(
                    f"Failed to fetch JWKS from {self._jwks_url}: {e}"
                ) from e

            jwks = PyJWKSet.from_dict(jwks_data)
            self._cache = _CachedJWKS(jwks=jwks, fetched_at=time.monotonic())
            return jwks
