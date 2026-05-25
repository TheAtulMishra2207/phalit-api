"""
Phalit.ai · FastAPI authentication dependencies.

This module is the bridge between incoming HTTP requests and Phalit's
business logic. It exposes two FastAPI dependency functions that routes
can use via `Depends()`:

    get_current_user           — Required auth. Raises 401 if no/invalid token.
    get_current_user_optional  — Optional auth. Returns None if no token.

What happens on each authenticated request:
  1. Extract the JWT from the `Authorization: Bearer ...` header
  2. Verify signature/expiry/claims via SupabaseJWTVerifier (uses JWKS cache)
  3. Look up the user's profile in public.profiles (via PostgREST + service_role)
  4. Resolve effective tier — respects tier_expires_at (expired → 'anveshak')
  5. Inject a frozen `CurrentUser` dataclass into the route handler

The verifier is instantiated lazily as a process-wide singleton, so the
JWKS cache is shared across all requests in this worker.

Usage from a route:

    from fastapi import Depends
    from dependencies import CurrentUser, get_current_user

    @app.get("/me")
    async def me(user: CurrentUser = Depends(get_current_user)):
        return {"user_id": user.user_id, "tier": user.tier, ...}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings
from jwt_verifier import (
    JWKSUnavailableError,
    JWTClaimsError,
    JWTExpiredError,
    JWTSignatureError,
    JWTVerificationError,
    SupabaseJWTVerifier,
)


# ============================================================================
# Security scheme — drives OpenAPI docs + header extraction
# auto_error=False so we can craft our own 401 with WWW-Authenticate header
# ============================================================================

_bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================================
# Resolved user context — what routes actually receive
# ============================================================================

@dataclass(frozen=True)
class CurrentUser:
    """
    Resolved authenticated user for a single request.
    Frozen so route handlers can't accidentally mutate per-request state.
    """
    user_id: str            # auth.users.id (UUID)
    tier: str               # effective tier, respects tier_expires_at
    profile: dict[str, Any] # full public.profiles row
    claims: dict[str, Any]  # raw JWT claims (sub, email, exp, role, ...)

    @property
    def email(self) -> str | None:
        return self.claims.get("email")

    @property
    def phone(self) -> str | None:
        return self.profile.get("phone") or self.claims.get("phone")


# ============================================================================
# Singleton verifier
# ============================================================================

@lru_cache(maxsize=1)
def get_jwt_verifier() -> SupabaseJWTVerifier:
    """Process-wide singleton, lazily instantiated on first request."""
    settings = get_settings()
    return SupabaseJWTVerifier(
        project_url=settings.supabase_url,
        cache_ttl_seconds=settings.jwt_cache_ttl_seconds,
        http_timeout_seconds=settings.jwt_http_timeout_seconds,
    )


# ============================================================================
# Internals
# ============================================================================

def _unauthorized(detail: str, error_code: str = "invalid_token") -> HTTPException:
    """RFC 6750 compliant 401 with WWW-Authenticate header."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": f'Bearer error="{error_code}"'},
    )


async def _fetch_profile(user_id: str) -> dict[str, Any] | None:
    """
    Fetch a profile row from Supabase via PostgREST.
    Uses the service_role key so RLS doesn't apply — backend always sees full row.
    Returns None if no row exists (which shouldn't happen post-signup-trigger).
    """
    settings = get_settings()
    rest_url = f"{settings.supabase_url}/rest/v1/profiles"
    headers = {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Accept": "application/json",
    }
    params = {
        "id": f"eq.{user_id}",
        "select": "*",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(rest_url, headers=headers, params=params)
            response.raise_for_status()
            rows = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Profile lookup failed: {e}",
        ) from e

    if not rows:
        return None
    return rows[0]


def _resolve_effective_tier(profile: dict[str, Any]) -> str:
    """
    Mirror the SQL public.current_user_tier() function in Python.
    If tier_expires_at is set and in the past, downgrade to 'anveshak'.
    """
    tier = profile.get("tier") or "anveshak"
    expires_raw = profile.get("tier_expires_at")
    if not expires_raw:
        return tier

    if isinstance(expires_raw, str):
        # Supabase returns ISO 8601; handle trailing 'Z' for older Python versions
        expires_str = expires_raw.replace("Z", "+00:00")
        try:
            expires = datetime.fromisoformat(expires_str)
        except ValueError:
            # Malformed timestamp — fail safe to current tier rather than crash
            return tier
    elif isinstance(expires_raw, datetime):
        expires = expires_raw
    else:
        return tier

    # Ensure timezone awareness for comparison
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires <= datetime.now(timezone.utc):
        return "anveshak"
    return tier


# ============================================================================
# Public dependencies — what routes import
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    Required-auth dependency. Use on every protected route.
    
    Raises:
        401 if header missing / token invalid / token expired / claims wrong
        503 if Supabase JWKS endpoint or PostgREST is unreachable
        404 if JWT is valid but no profile row exists (signup trigger failed)
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Missing Authorization: Bearer header")

    token = credentials.credentials
    verifier = get_jwt_verifier()

    try:
        claims = await verifier.verify(token)
    except JWTExpiredError:
        raise _unauthorized("Token expired", error_code="token_expired")
    except (JWTSignatureError, JWTClaimsError) as e:
        raise _unauthorized(f"Invalid token: {e}")
    except JWKSUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )
    except JWTVerificationError as e:
        raise _unauthorized(f"Token verification failed: {e}")

    user_id = claims.get("sub")
    if not user_id:
        raise _unauthorized("Token missing 'sub' claim")

    profile = await _fetch_profile(user_id)
    if profile is None:
        # Signup trigger should have created this row. If it's missing,
        # something is wrong upstream — surface clearly rather than silently 401.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No profile found for user_id={user_id}",
        )

    return CurrentUser(
        user_id=user_id,
        tier=_resolve_effective_tier(profile),
        profile=profile,
        claims=claims,
    )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser | None:
    """
    Optional-auth dependency. Use on routes that serve both anonymous and
    authenticated users — e.g., locked-content pages with tier-aware messaging.
    
    Behavior:
        - No Authorization header → return None (treat as anonymous)
        - Header present but invalid → still raise 401 (don't silently treat
          a broken token as anonymous; that masks bugs in the frontend)
    """
    if credentials is None or not credentials.credentials:
        return None
    return await get_current_user(credentials=credentials)
