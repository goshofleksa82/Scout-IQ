"""Current-user account management. Roles are never publicly editable."""
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.core.database import get_db
from app.models import User, RefreshSession
from app.schemas import UserProfileUpdate, PasswordChange, UserResponse
from app.core.security import hash_password, verify_password
from app.services.sessions import clear_refresh_cookie

router = APIRouter(prefix="/users", tags=["Account"])
logger = logging.getLogger(__name__)


@router.patch("/me", response_model=UserResponse)
def update_profile(data: UserProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return user
    try:
        for name, value in changes.items():
            setattr(user, name, str(value))
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already registered") from None
    except SQLAlchemyError:
        db.rollback()
        logger.error("Profile update failed")
        raise HTTPException(status_code=500, detail="Unable to update profile") from None


@router.post("/me/change-password", status_code=204)
def change_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        request_version = user.token_version
        locked = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
        if locked is None or locked.token_version != request_version:
            raise HTTPException(status_code=401, detail="Session expired; log in again")
        if not verify_password(data.current_password.get_secret_value(), locked.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        if data.current_password.get_secret_value() == data.new_password.get_secret_value():
            raise HTTPException(status_code=400, detail="New password must differ from current password")
        locked.hashed_password = hash_password(data.new_password.get_secret_value())
        locked.token_version += 1
        db.execute(update(RefreshSession).where(RefreshSession.user_id == locked.id,
            RefreshSession.revoked_at.is_(None)).values(revoked_at=datetime.now(timezone.utc)))
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.error("Password change failed")
        raise HTTPException(status_code=500, detail="Unable to change password") from None
    response = Response(status_code=204)
    clear_refresh_cookie(response)
    return response
