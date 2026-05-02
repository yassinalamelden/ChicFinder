"""
Firebase authentication dependency for FastAPI routes.

Provides a Depends() function to verify Firebase ID tokens on protected endpoints.
"""

import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK once
_firebase_app = None


def _init_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    global _firebase_app
    if _firebase_app is not None:
        return

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    try:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with service account file")
        else:
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with application default credentials")
    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", str(e))
        raise


_bearer = HTTPBearer()


async def require_auth(
    token: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Verify Firebase ID token in Authorization header.

    Expected header format: Authorization: Bearer <firebase_id_token>

    Returns:
        dict: Decoded token claims, including 'uid' and other user info

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    _init_firebase()

    try:
        decoded = auth.verify_id_token(token.credentials)
        return decoded
    except auth.InvalidIdTokenError:
        logger.warning("Invalid ID token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    except auth.ExpiredIdTokenError:
        logger.warning("Expired ID token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except Exception as e:
        logger.error("Token verification failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
