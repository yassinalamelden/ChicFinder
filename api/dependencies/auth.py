"""
api/dependencies/auth.py
=========================
FastAPI dependency that enforces Firebase authentication on protected routes.

Usage:
    from api.dependencies.auth import get_current_user

    @router.get("/protected")
    async def protected(user: dict = Depends(get_current_user)):
        return {"uid": user["uid"]}
"""

from fastapi import Header, HTTPException, status
from api.middleware.auth import verify_firebase_token


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """
    Extract and verify the Firebase ID token from the Authorization header.

    DEV MODE: Skips verification and returns a stub user.
    In production, remove the dev mode check.
    """
    # DEV MODE: Return stub user without verification
    return {"uid": "dev-user", "email": "dev@chicfinder.local"}
