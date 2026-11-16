
import logging

import jwt

from fastapi import (
    APIRouter, Depends, HTTPException,
    status, Request, Response
)
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.services.sessions import (COOKIE_NAME, InvalidRefresh, check_origin, clear_refresh_cookie,
                      issue_session, logout_session, rotate_session, set_refresh_cookie)
from app.schemas import (
    UserCreate, UserResponse,
    LoginRequest, TokenResponse
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_claims,
    DUMMY_PASSWORD_HASH,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
from app.core.dependencies import get_current_user, require_admin, unauthorized


async def safe_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path.rstrip("/") in {"/auth/register", "/auth/login"} or request.url.path.startswith("/users/"):
        # FastAPI's default validation errors echo rejected inputs. Do not echo
        # passwords (including passwords nested in a malformed request body).
        errors = [
            {key: error[key] for key in ("type", "loc", "msg")}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})
    return await request_validation_exception_handler(request, exc)








@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    username = data.username
    email = str(data.email)

    try:
        existing = db.query(User).filter(
            or_(
                User.username == username,
                User.email == email
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Username or email already registered"
            )

        try:
            hashed_password = hash_password(data.password.get_secret_value())
        except Exception:
            logger.error("Password hashing failure")
            raise HTTPException(status_code=500, detail="Unable to register user") from None

        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role="viewer",
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Username or email already registered"
        ) from None

    except SQLAlchemyError:
        db.rollback()
        logger.error("Registration database failure")
        raise HTTPException(
            status_code=500,
            detail="Unable to register user"
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    check_origin(request)
    try:
        user = db.query(User).filter(
            User.username == data.username
        ).with_for_update().populate_existing().first()

    except SQLAlchemyError:
        db.rollback()
        logger.error("Login database failure")
        raise HTTPException(
            status_code=500,
            detail="Authentication service unavailable"
        ) from None

    try:
        valid_password = verify_password(
            data.password.get_secret_value(),
            user.hashed_password if user is not None else DUMMY_PASSWORD_HASH,
        )
    except Exception:
        logger.error("Password verification failure")
        raise HTTPException(
            status_code=500,
            detail="Authentication service unavailable"
        ) from None

    if (
        user is None
        or not valid_password
        or not user.is_active
    ):
        raise unauthorized()

    try:
        issued_user_id, issued_version = user.id, user.token_version
        raw = issue_session(db, user)
    except SQLAlchemyError:
        db.rollback()
        logger.error("Session creation failed")
        raise HTTPException(status_code=500, detail="Authentication service unavailable") from None
    set_refresh_cookie(response, raw)
    return TokenResponse(
        access_token=create_access_token(issued_user_id, issued_version)
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    try:
        user_id, version, raw = rotate_session(db, request.cookies.get(COOKIE_NAME, ""))
    except InvalidRefresh:
        failure = JSONResponse(status_code=401, content={"detail": "Invalid or expired refresh session"},
                               headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"})
        clear_refresh_cookie(failure)
        return failure
    except SQLAlchemyError:
        db.rollback()
        logger.error("Session refresh failed")
        raise HTTPException(status_code=500, detail="Authentication service unavailable") from None
    set_refresh_cookie(response, raw)
    return TokenResponse(access_token=create_access_token(user_id, version))


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    check_origin(request)
    try:
        logout_session(db, request.cookies.get(COOKIE_NAME, ""))
    except SQLAlchemyError:
        db.rollback()
        logger.error("Session logout failed")
        raise HTTPException(status_code=500, detail="Authentication service unavailable") from None
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    clear_refresh_cookie(response)
    return response
