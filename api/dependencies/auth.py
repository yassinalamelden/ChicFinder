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

    Raises HTTP 401 if the token is absent or invalid.
    """
    decoded = verify_firebase_token(authorization)
    if decoded is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decoded
