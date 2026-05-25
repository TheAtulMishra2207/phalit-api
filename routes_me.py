"""
Phalit.ai · /me endpoint.

Returns everything the frontend needs to render the authenticated user's
session state: identity, tier, tier window, and kundali slot usage.

Mount this in main.py with one line:

    from routes_me import router as me_router
    app.include_router(me_router)

Route:
    GET /me  →  requires Authorization: Bearer <supabase_jwt>
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from config import get_settings
from dependencies import CurrentUser, get_current_user


# ----------------------------------------------------------------------------
# Per-tier kundali slot limits.
# This mirrors public.can_save_kundali() in the SQL schema — duplicating
# intentionally so the frontend gets the limit in one call without an extra
# RPC. When more endpoints need these numbers, extract to tier_limits.py.
# ----------------------------------------------------------------------------
TIER_KUNDALI_LIMITS: dict[str, int] = {
    "anveshak":    1,
    "prajna":      5,
    "shodhak":    25,
    "vishleshak": 100,
    "pandit":   1000,
}


router = APIRouter(prefix="/me", tags=["me"])


async def _count_kundalis(user_id: str) -> int:
    """
    Count saved kundalis for `user_id` via PostgREST.
    Uses Prefer: count=exact so PostgREST returns the total in Content-Range,
    avoiding the cost of fetching actual rows just to count them.
    """
    settings = get_settings()
    rest_url = f"{settings.supabase_url}/rest/v1/kundalis"
    headers = {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Accept": "application/json",
        "Prefer": "count=exact",
    }
    params = {
        "user_id": f"eq.{user_id}",
        "select": "id",
        "limit": "1",  # we only want the count, not the rows
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(rest_url, headers=headers, params=params)
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Kundali count lookup failed: {e}",
        ) from e

    # Content-Range header format: "0-0/<total>" with rows, "*/0" when empty
    content_range = response.headers.get("Content-Range", "*/0")
    try:
        return int(content_range.split("/")[-1])
    except (ValueError, IndexError):
        return 0


@router.get(
    "",
    summary="Get the current user's profile, tier, and slot usage",
)
async def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    """
    Frontend uses this to populate the session state on every page load:

    {
        "user_id":         "<uuid>",
        "email":           "user@example.com",
        "name":            "...",
        "phone":           "...",
        "tier":            "anveshak",
        "tier_started_at": "2026-05-23T12:55:29Z",
        "tier_expires_at": null,
        "referral_code":   "F5A12BDB",
        "marketing_opt_in": false,
        "kundalis": {
            "count":     0,
            "limit":     1,
            "remaining": 1
        }
    }

    Tier respects tier_expires_at — if expired, you'll see tier='anveshak'
    here even if profiles.tier still says 'pandit'.
    """
    count = await _count_kundalis(user.user_id)
    limit = TIER_KUNDALI_LIMITS.get(user.tier, 1)

    return {
        "user_id":          user.user_id,
        "email":            user.email,
        "name":             user.profile.get("name"),
        "phone":            user.profile.get("phone"),
        "tier":             user.tier,
        "tier_started_at":  user.profile.get("tier_started_at"),
        "tier_expires_at":  user.profile.get("tier_expires_at"),
        "referral_code":    user.profile.get("referral_code"),
        "marketing_opt_in": user.profile.get("marketing_opt_in", False),
        "kundalis": {
            "count":     count,
            "limit":     limit,
            "remaining": max(0, limit - count),
        },
    }
