"""Authentication and role dependencies shared by every router."""
import logging
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_claims
from app.models import User
from app.core.auditing import set_actor
logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db)
) -> User:
    if credentials is None:
        raise unauthorized()

    try:
        user_id, token_version = decode_access_claims(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized() from None

    try:
        user = db.get(User, user_id)
    except SQLAlchemyError:
        db.rollback()
        logger.error("User lookup failed")
        raise HTTPException(
            status_code=500,
            detail="Authentication service unavailable"
        ) from None

    if user is None or not user.is_active or user.token_version != token_version:
        raise unauthorized()

    set_actor(db,user.id)
    return user


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permissions required"
        )

    return current_user

