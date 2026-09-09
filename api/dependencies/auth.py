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

    # In production, always require a verified token — never fall back to the
    # dev stub, even if Firebase credentials aren't configured. A missing
    # credential should make auth fail closed, not silently permit everyone.
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fall back to dev stub when credentials are not configured
    return {"uid": "dev-user", "email": "dev@chicfinder.local"}


async def get_optional_user(authorization: str = Header(default=None)):
    """
    Identify the caller when possible, and let them through when not.

    For endpoints that are open to everyone but still worth attributing when a
    signed-in person uses them. Photo search is the case that matters: making it
    require an account turns the app's first action into a sign-up wall, which
    is the opposite of the product. Returns None for a guest, and also for a
    token that fails to verify: a bad token is a guest, not an error, on a route
    that does not need one.
    """
    if not authorization:
        return None
    return verify_firebase_token(authorization)
