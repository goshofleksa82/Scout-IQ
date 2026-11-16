"""Opaque refresh tokens, rotation, and replay revocation for cookie sessions."""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import uuid4

from fastapi import HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshSession, User
from app.core.config import settings

COOKIE_NAME = "scoutiq_refresh"
COOKIE_PATH = "/auth"
REFRESH_DAYS = settings.refresh_days
COOKIE_SECURE = settings.environment in {"staging","production"}


class InvalidRefresh(Exception):
    pass


def check_origin(request: Request):
    origin = request.headers.get("origin")
    allowed = {str(request.base_url).rstrip("/")}
    allowed.update(settings.allowed_origins)
    if origin is not None and origin not in allowed:
        raise HTTPException(status_code=403, detail="Untrusted session request origin")


def token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_session(user_id, family_id=None, expires_at=None):
    now = datetime.now(timezone.utc)
    raw = secrets.token_urlsafe(48)
    row = RefreshSession(
        id=str(uuid4()), family_id=family_id or str(uuid4()), user_id=user_id,
        token_hash=token_digest(raw), created_at=now,
        expires_at=expires_at or now + timedelta(days=REFRESH_DAYS),
    )
    return row, raw


def issue_session(db: Session, user: User) -> str:
    row, raw = _new_session(user.id)
    db.add(row)
    db.commit()
    return raw


def _find_locked(db: Session, raw: str):
    if not raw or len(raw) > 128:
        return None, None
    row = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_digest(raw)))
    if row is None:
        return None, None
    # Serialize refresh/logout for an account, including different rotated
    # tokens. Reload after acquiring the lock so concurrent replays see updates.
    user = db.scalar(select(User).where(User.id == row.user_id).with_for_update())
    row = db.scalar(select(RefreshSession).where(RefreshSession.id == row.id)
                    .with_for_update().execution_options(populate_existing=True))
    return row, user


def revoke_family(db: Session, family_id: str):
    db.execute(update(RefreshSession).where(
        RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None),
    ).values(revoked_at=datetime.now(timezone.utc)))


def rotate_session(db: Session, raw: str):
    row, user = _find_locked(db, raw)
    now = datetime.now(timezone.utc)
    if row is None:
        raise InvalidRefresh()
    if row.revoked_at is not None:
        # A rotated token replay revokes every descendant, not just the replay.
        revoke_family(db, row.family_id)
        db.commit()
        raise InvalidRefresh()
    if row.expires_at <= now or user is None or not user.is_active:
        revoke_family(db, row.family_id)
        db.commit()
        raise InvalidRefresh()
    replacement, raw_replacement = _new_session(user.id, row.family_id, row.expires_at)
    row.revoked_at, row.replaced_by = now, replacement.id
    db.add(replacement)
    user_id, version = user.id, user.token_version
    db.commit()
    return user_id, version, raw_replacement


def logout_session(db: Session, raw: str):
    row, _ = _find_locked(db, raw)
    if row is not None:
        revoke_family(db, row.family_id)
        db.commit()


def set_refresh_cookie(response: Response, raw: str):
    response.set_cookie(COOKIE_NAME, raw, max_age=REFRESH_DAYS * 86400,
                        httponly=True, secure=COOKIE_SECURE, samesite="lax", path=COOKIE_PATH)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def clear_refresh_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, secure=COOKIE_SECURE,
                           httponly=True, samesite="lax")
