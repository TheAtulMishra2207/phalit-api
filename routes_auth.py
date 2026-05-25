"""
Phalit.ai · authenticated user lifecycle routes.

Current endpoints:
    DELETE /auth/delete-me   — DPDPA-compliant account deletion

Future endpoints in this file:
    POST   /auth/change-email     — email change with verification
    POST   /auth/change-password  — password change

Mount in main.py:
    from routes_auth import router as auth_router
    app.include_router(auth_router)
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status

from config import get_settings
from dependencies import CurrentUser, get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


async def _supabase_admin_delete_user(user_id: str) -> None:
    """
    Delete the auth.users row via Supabase Admin API.
    Our schema's `on delete cascade` chain then removes the dependent rows
    (profiles, kundalis, subscriptions, tier_events) atomically.

    Requires the service_role secret key — uses an admin endpoint, not PostgREST.
    """
    settings = get_settings()
    admin_url = f"{settings.supabase_url}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(admin_url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Supabase returned a 4xx/5xx — surface its body for diagnosis
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase rejected delete: {e.response.text}",
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Supabase admin API: {e}",
        ) from e


@router.delete(
    "/delete-me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete the authenticated user and all their data",
    description=(
        "DPDPA-compliant immediate account deletion. Irreversible. "
        "Removes the auth.users row; FK cascade then removes the user's "
        "profile, saved kundalis, subscription records, and tier-event audit log. "
        "Frontend MUST show a confirmation modal before calling this."
    ),
)
async def delete_me(
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """
    Immediate, irreversible account deletion.

    What gets deleted:
      - auth.users row              (via Supabase Admin API)
      - public.profiles row         (FK cascade)
      - public.kundalis rows        (FK cascade — all the user's saved charts)
      - public.subscriptions rows   (FK cascade)
      - public.tier_events rows     (FK cascade)

    What does NOT get deleted (and stays elsewhere by design):
      - Razorpay payment records — retained in Razorpay per tax/legal compliance
      - Server logs containing the user_id UUID — rotated out by Render's retention policy

    The token used to authenticate this request remains cryptographically valid
    until its `exp` claim, but every subsequent request will fail at the
    profile lookup step (returns 404), which the frontend should treat as
    "logged out." See the post-deploy note about hardening dependencies.py.

    Returns:
        204 No Content on success.

    Raises:
        401 if not authenticated
        502 if Supabase Admin API rejects the delete
        503 if Supabase is unreachable
    """
    await _supabase_admin_delete_user(user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
