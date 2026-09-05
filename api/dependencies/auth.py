"""
Firebase authentication dependency for FastAPI routes.
"""

import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)

_firebase_app = None


def _init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    project_id = os.getenv("FIREBASE_PROJECT_ID")

    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase initialized with service account: %s", cred_path)
    elif project_id:
        # No service account — initialize with project ID only.
        # Sufficient for verify_id_token; tokens are checked against
        # Google's public keys via network without admin privileges.
        _firebase_app = firebase_admin.initialize_app(options={"projectId": project_id})
        logger.info("Firebase initialized with project ID: %s", project_id)
    else:
        logger.warning(
            "Neither FIREBASE_SERVICE_ACCOUNT_PATH nor FIREBASE_PROJECT_ID is set. "
            "Set FIREBASE_PROJECT_ID in .env to enable token verification."
        )
        try:
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with application default credentials")
        except Exception as e:
            logger.error("Firebase ADC initialization failed: %s", e)
            raise


_bearer = HTTPBearer()


async def require_auth(
    token: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    _init_firebase()

    try:
        decoded = auth.verify_id_token(token.credentials, check_revoked=False)
        return decoded
    except auth.ExpiredIdTokenError as e:
        logger.warning("Expired token: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired — please sign in again")
    except auth.InvalidIdTokenError as e:
        logger.warning("Invalid token (%s): %s", type(e).__name__, e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {type(e).__name__}")
    except Exception as e:
        logger.error("Token verification failed (%s): %s", type(e).__name__, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Auth error: {type(e).__name__}: {e}")
