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


async def get_current_user(authorization: str = Header(default=None)) -> dict:
    """
    Extract and verify the Firebase ID token from the Authorization header.

    In development mode (APP_ENV != "production"), returns a stub user without verification.
    In production, verifies the token against Firebase Admin SDK and raises 401 on failure.
    """
    from chic_finder.config import settings

    # Try to verify the token
    if authorization:
        user = verify_firebase_token(authorization)
        if user:
            return user

    # If we're in production and got here, the token is invalid or missing
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development, allow requests without a valid token
    return {"uid": "dev-user", "email": "dev@chicfinder.local"}
