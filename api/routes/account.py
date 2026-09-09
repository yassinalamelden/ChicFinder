"""
api/routes/account.py
======================
Account management for the mobile app.

Routes:
  GET    /api/v1/account   → the caller's own account summary
  DELETE /api/v1/account   → permanently delete the account and its data

App Store Guideline 5.1.1(v) requires any app that lets a user create an account
to also let them delete it from inside the app, and the deletion has to remove
the account itself, not merely deactivate it or sign the user out. So the DELETE
here does two things in order:

  1. Deletes every row this service holds for the uid.
  2. Deletes the Firebase Auth user, which invalidates their credentials.

Data is deleted before the auth record so a failure at step 2 leaves no orphaned
rows behind. A failed step 2 is reported as an error rather than swallowed, so
the app can tell the user honestly that deletion did not complete.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependencies.auth import get_current_user
from chic_finder import db
from chic_finder.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class AccountResponse(BaseModel):
    uid: str
    email: Optional[str] = None


class DeletionResponse(BaseModel):
    deleted: bool
    rows_removed: int
    auth_record_removed: bool
    message: str


def _delete_firebase_user(uid: str) -> bool:
    """Deletes the Firebase Auth record. Returns False if it could not be done.

    Outside production the app runs without Firebase credentials and every
    request maps to the same stub uid, so there is no auth record to remove and
    this is a no-op that reports success.
    """
    if settings.APP_ENV != "production":
        logger.info("Development mode: skipping Firebase user deletion for %s", uid)
        return True

    try:
        from api.middleware.auth import _init_firebase

        if not _init_firebase():
            logger.error("Firebase Admin not initialised; cannot delete uid=%s", uid)
            return False

        from firebase_admin import auth as firebase_auth

        firebase_auth.delete_user(uid)
        return True
    except Exception as exc:
        logger.error("Firebase user deletion failed for uid=%s: %s", uid, exc)
        return False


# ---------------------------------------------------------------------------
# GET /account
# ---------------------------------------------------------------------------

@router.get("/account", response_model=AccountResponse)
async def get_account(user: dict = Depends(get_current_user)):
    """Returns the caller's own account summary."""
    return AccountResponse(uid=user["uid"], email=user.get("email"))


# ---------------------------------------------------------------------------
# DELETE /account
# ---------------------------------------------------------------------------

@router.delete("/account", response_model=DeletionResponse)
async def delete_account(user: dict = Depends(get_current_user)):
    """Permanently deletes the caller's account and all data held for it."""
    uid = user["uid"]

    try:
        rows_removed = await run_in_threadpool(db.delete_all_user_data, uid)
    except Exception as exc:
        logger.error("Account data deletion failed for uid=%s: %s", uid, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not delete your data right now. Please try again.",
        )

    auth_removed = await run_in_threadpool(_delete_firebase_user, uid)

    if not auth_removed:
        # The data is gone but the login still exists. Say so rather than
        # claiming a deletion that did not fully happen.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Your saved data was deleted, but your sign-in record could not "
                "be removed. Please contact support@chicfinder.app so we can "
                "finish deleting your account."
            ),
        )

    logger.info("Account deleted: uid=%s rows_removed=%d", uid, rows_removed)

    return DeletionResponse(
        deleted=True,
        rows_removed=rows_removed,
        auth_record_removed=True,
        message="Your account and all associated data have been permanently deleted.",
    )
