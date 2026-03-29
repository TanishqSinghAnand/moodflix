"""
FastAPI dependency that extracts and verifies a Firebase ID token from
the Authorization header. Reusable across all protected routes.

Usage:
    @router.get("/protected")
    async def route(user: dict = Depends(get_current_user)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError

from app.services.firebase import verify_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Verify Firebase JWT. Returns decoded token claims including:
    - uid: str
    - email: str | None
    - name: str | None
    """
    try:
        decoded = verify_token(creds.credentials)
        return decoded
    except ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please sign in again.",
        )
    except InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth error: {str(exc)}",
        )
