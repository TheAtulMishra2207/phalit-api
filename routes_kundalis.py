"""
Phalit.ai · kundali CRUD routes.

Endpoints:
    GET    /kundalis           — list user's saved kundalis (lean metadata)
    GET    /kundalis/{id}      — fetch one kundali in full (chart_data + narratives)
    POST   /kundalis           — save a new kundali (enforces tier slot limit)
    PATCH  /kundalis/{id}      — update any subset of fields
    DELETE /kundalis/{id}      — permanently delete one

Ownership is enforced two ways:
    1. Backend uses service_role to bypass RLS — must check user_id explicitly
       on EVERY query (belt-and-suspenders, not just RLS)
    2. Every PostgREST call includes user_id=eq.{caller} in the filter, so
       a malicious id-guess can't return another user's row

Mount in main.py:
    from routes_kundalis import router as kundalis_router
    app.include_router(kundalis_router)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from config import get_settings
from dependencies import CurrentUser, get_current_user


# ----------------------------------------------------------------------------
# Per-tier kundali slot limits.
# Duplicated from routes_me.py — when a third use-case emerges, extract this
# (plus future per-tier limits like prashna_per_month) into tier_limits.py.
# ----------------------------------------------------------------------------
TIER_KUNDALI_LIMITS: dict[str, int] = {
    "anveshak":    1,
    "prajna":      5,
    "shodhak":    25,
    "vishleshak": 100,
    "pandit":   1000,
}


router = APIRouter(prefix="/kundalis", tags=["kundalis"])


# ============================================================================
# Pydantic request/response models
# ============================================================================

class KundaliCreate(BaseModel):
    """Body for POST /kundalis. All fields required."""
    name:        str           = Field(..., min_length=1, max_length=200)
    birth_dt:    datetime
    birth_lat:   float         = Field(..., ge=-90.0,  le=90.0)
    birth_lon:   float         = Field(..., ge=-180.0, le=180.0)
    birth_place: str           = Field(..., min_length=1, max_length=500)
    chart_data:  dict[str, Any]
    cached_narratives: Optional[dict[str, Any]] = None


class KundaliUpdate(BaseModel):
    """
    Body for PATCH /kundalis/{id}. All fields optional —
    we only update the fields the caller actually provided.
    """
    name:        Optional[str]   = Field(None, min_length=1, max_length=200)
    birth_dt:    Optional[datetime] = None
    birth_lat:   Optional[float] = Field(None, ge=-90.0,  le=90.0)
    birth_lon:   Optional[float] = Field(None, ge=-180.0, le=180.0)
    birth_place: Optional[str]   = Field(None, min_length=1, max_length=500)
    chart_data:  Optional[dict[str, Any]] = None
    cached_narratives: Optional[dict[str, Any]] = None


# ============================================================================
# Internal helpers
# ============================================================================

async def _supabase_request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: Any = None,
    headers_extra: dict | None = None,
) -> httpx.Response:
    """
    Authenticated request to Supabase PostgREST using service_role.
    Centralized so error handling is uniform across all kundali operations.
    """
    settings = get_settings()
    url = f"{settings.supabase_url}/rest/v1{path}"
    headers = {
        "apikey":        settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }
    if headers_extra:
        headers.update(headers_extra)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method, url, params=params, json=json, headers=headers,
            )
            response.raise_for_status()
            return response
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase rejected request: {e.response.text}",
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Supabase: {e}",
        ) from e


async def _count_user_kundalis(user_id: str) -> int:
    """Count kundalis owned by user_id via Content-Range header trick."""
    response = await _supabase_request(
        "GET",
        "/kundalis",
        params={"user_id": f"eq.{user_id}", "select": "id", "limit": "1"},
        headers_extra={"Prefer": "count=exact"},
    )
    content_range = response.headers.get("Content-Range", "*/0")
    try:
        return int(content_range.split("/")[-1])
    except (ValueError, IndexError):
        return 0


def _serialize_for_postgrest(body: dict[str, Any]) -> dict[str, Any]:
    """
    Convert Pydantic-emitted Python types to JSON-safe values for PostgREST.
    Currently just handles datetime → ISO 8601 string.
    """
    if isinstance(body.get("birth_dt"), datetime):
        body["birth_dt"] = body["birth_dt"].isoformat()
    return body


# ============================================================================
# Routes
# ============================================================================

@router.get(
    "",
    summary="List the user's saved kundalis",
)
async def list_kundalis(
    user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Lean list of all kundalis owned by the user. Sorted newest-first.
    Excludes chart_data and cached_narratives (potentially large JSONB blobs).
    Use GET /kundalis/{id} to fetch one in full.
    """
    response = await _supabase_request(
        "GET",
        "/kundalis",
        params={
            "user_id": f"eq.{user.user_id}",
            "select":  "id,name,birth_dt,birth_place,created_at,updated_at",
            "order":   "created_at.desc",
        },
    )
    return response.json()


@router.get(
    "/{kundali_id}",
    summary="Get one kundali in full (chart_data + cached_narratives)",
)
async def get_kundali(
    kundali_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Returns the complete kundali row.
    404 if not found OR owned by a different user — we deliberately don't
    distinguish, to avoid leaking the existence of other users' kundalis.
    """
    response = await _supabase_request(
        "GET",
        "/kundalis",
        params={
            "id":      f"eq.{kundali_id}",
            "user_id": f"eq.{user.user_id}",
            "select":  "*",
            "limit":   "1",
        },
    )
    rows = response.json()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kundali not found",
        )
    return rows[0]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Save a new kundali (subject to tier slot limit)",
)
async def create_kundali(
    payload: KundaliCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Saves a new kundali for the current user.

    Enforces the per-tier slot limit:
        anveshak: 1, prajna: 5, shodhak: 25, vishleshak: 100, pandit: 1000

    Returns:
        201 Created + the inserted row (including its new UUID)

    Raises:
        409 Conflict if the user is already at their tier's slot limit
            (detail names the limit and current count, so the frontend
             can render an accurate upgrade prompt)
    """
    # Best-effort slot enforcement — pre-launch traffic doesn't warrant a
    # DB-level race lock. Add a row-count trigger if abuse becomes a thing.
    count = await _count_user_kundalis(user.user_id)
    limit = TIER_KUNDALI_LIMITS.get(user.tier, 1)
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Slot limit reached: tier '{user.tier}' allows {limit} "
                f"kundali(s), you have {count}. Upgrade to save more."
            ),
        )

    body = _serialize_for_postgrest(payload.dict(exclude_none=True))
    body["user_id"] = user.user_id

    response = await _supabase_request(
        "POST",
        "/kundalis",
        json=body,
        headers_extra={"Prefer": "return=representation"},
    )
    rows = response.json()
    if not rows:
        # Defensive — return=representation should always echo the inserted row
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the inserted row",
        )
    return rows[0]


@router.patch(
    "/{kundali_id}",
    summary="Update any subset of editable fields on a kundali",
)
async def update_kundali(
    kundali_id: UUID,
    payload: KundaliUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Partial update — only fields actually present in the request body
    are touched. Useful for rename-only flows or for caching new narratives
    into cached_narratives without re-sending chart_data.

    Returns:
        200 OK + the updated row

    Raises:
        400 if the request body is empty (nothing to update)
        404 if the kundali doesn't exist or isn't owned by the caller
    """
    body = _serialize_for_postgrest(payload.dict(exclude_unset=True))
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    response = await _supabase_request(
        "PATCH",
        "/kundalis",
        params={
            "id":      f"eq.{kundali_id}",
            "user_id": f"eq.{user.user_id}",
        },
        json=body,
        headers_extra={"Prefer": "return=representation"},
    )
    rows = response.json()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kundali not found",
        )
    return rows[0]


@router.delete(
    "/{kundali_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a kundali",
)
async def delete_kundali(
    kundali_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """
    Permanently delete a single kundali.

    Returns:
        204 No Content on success

    Raises:
        404 if the kundali doesn't exist or isn't owned by the caller
    """
    response = await _supabase_request(
        "DELETE",
        "/kundalis",
        params={
            "id":      f"eq.{kundali_id}",
            "user_id": f"eq.{user.user_id}",
        },
        headers_extra={"Prefer": "return=representation"},
    )
    rows = response.json()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kundali not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
