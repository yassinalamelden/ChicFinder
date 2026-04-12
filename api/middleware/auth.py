"""
api/middleware/auth.py
======================
Firebase Admin SDK token verification.

Usage:
    from api.middleware.auth import verify_firebase_token
    decoded = verify_firebase_token("Bearer eyJ...")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-initialise Firebase Admin so the app can still start even if
# the credentials file is absent (e.g. during local dev without Firebase).
_firebase_initialised = False


def _init_firebase() -> bool:
    global _firebase_initialised
    if _firebase_initialised:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials
        from chic_finder.config import settings

        if not firebase_admin._apps:
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                # Initialise with default credentials (works when running on GCP
                # or when GOOGLE_APPLICATION_CREDENTIALS env var is set).
                firebase_admin.initialize_app()

        _firebase_initialised = True
        return True
    except Exception as exc:
        logger.warning("Firebase Admin SDK not initialised: %s", exc)
        return False


def verify_firebase_token(authorization: str) -> Optional[dict]:
    """
    Verify a Firebase ID token from the Authorization header.

    Args:
        authorization: The raw ``Authorization`` header value,
                       expected format: ``Bearer <id_token>``.

    Returns:
        The decoded token payload dict on success, or ``None`` on failure.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    if not _init_firebase():
        # Firebase not configured — in dev mode, return a stub user so the
        # app remains usable without credentials.
        logger.warning("Firebase not configured; returning stub user for dev mode.")
        return {"uid": "dev-user", "email": "dev@chicfinder.local"}

    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception as exc:
        logger.warning("Token verification failed: %s", exc)
        return None
