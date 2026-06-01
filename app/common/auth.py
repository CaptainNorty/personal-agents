"""
Auth dependency for Unknown Unknowns endpoints.

Verifies a Firebase ID token from the `Authorization: Bearer ...` header on
every request, then find-or-creates the corresponding `User` row keyed by
the Firebase UID.

The frontend calls `auth.currentUser.getIdToken()` (Firebase JS SDK) before
each request and attaches the token as a Bearer header. IDtokens are short-
lived (~1 hour); the SDK auto-refreshes them via the refresh token held in
IndexedDB, so the user stays signed in until they explicitly sign out.

For deploys, Firebase Admin reads the service account key from
`settings.firebase_admin_key_path` (defaults to a gitignored file under
`app/secrets/`).
"""

from __future__ import annotations

import firebase_admin
from fastapi import Depends, Header, HTTPException, status
from firebase_admin import auth as firebase_auth, credentials
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.unknownUnknowns.models import User


def _init_firebase_admin() -> None:
    """Initialize the Admin SDK once, lazily. Safe to call repeatedly."""
    if firebase_admin._apps:
        return
    cred = credentials.Certificate(settings.firebase_admin_key_path)
    firebase_admin.initialize_app(cred)
    logger.info(
        f"[uu auth] Firebase Admin initialized "
        f"(key={settings.firebase_admin_key_path})"
    )


_init_firebase_admin()


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Verify the Firebase ID token in the Authorization header and return
    the matching User row (creating one on first sign-in)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = firebase_auth.verify_id_token(token)
    except firebase_auth.ExpiredIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token expired — refresh and retry.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (firebase_auth.RevokedIdTokenError, firebase_auth.InvalidIdTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        # Catchall — covers FirebaseError, network issues during cert fetch, etc.
        logger.exception("[uu auth] Unexpected ID-token verification failure.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    uid = claims["uid"]
    email = claims.get("email")

    result = await session.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalar_one_or_none()
    if user is not None:
        # Refresh email if the user updated it in Google.
        if email and user.email != email:
            user.email = email
            await session.commit()
        return user

    user = User(firebase_uid=uid, email=email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info(f"[uu auth] First sign-in for uid={uid} email={email!r}")
    return user
