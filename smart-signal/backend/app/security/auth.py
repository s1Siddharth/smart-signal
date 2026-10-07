"""
security/auth.py — Firebase ID token verification + email allowlist.
"""
from __future__ import annotations

import os
import json
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import ALLOWED_EMAILS

_bearer = HTTPBearer(auto_error=False)

# Firebase Admin SDK — initialised lazily
_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json:
        # Running without Firebase (dev mode) — skip verification
        return None

    try:
        import firebase_admin  # type: ignore
        from firebase_admin import credentials  # type: ignore

        if not firebase_admin._apps:
            cred = credentials.Certificate(json.loads(sa_json))
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            _firebase_app = firebase_admin.get_app()
    except Exception as exc:
        print(f"[auth] Firebase init failed: {exc}")
        _firebase_app = None

    return _firebase_app


def verify_token(token: str) -> dict:
    """Verify a Firebase ID token. Returns the decoded token dict."""
    app = _get_firebase_app()
    if app is None:
        # Dev mode: accept any token string as the email
        return {"email": token, "uid": token}

    try:
        from firebase_admin import auth  # type: ignore
        return auth.verify_id_token(token, app=app)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )


def _check_allowlist(email: Optional[str]) -> None:
    if not ALLOWED_EMAILS:
        return  # No allowlist configured — allow all authenticated users
    if not email or email not in ALLOWED_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not in allowed list.",
        )


async def require_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """FastAPI dependency: verify token + allowlist."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )
    decoded = verify_token(creds.credentials)
    _check_allowlist(decoded.get("email"))
    return decoded
