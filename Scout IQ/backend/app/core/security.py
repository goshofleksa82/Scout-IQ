
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from app.core.config import settings

password_hash = PasswordHash.recommended()

JWT_SECRET_KEY = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_minutes

# Unknown usernames still perform an Argon2 verification. This is a random dummy
# value, never a usable account or a configured credential.
DUMMY_PASSWORD_HASH = password_hash.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


def create_access_token(user_id: int, token_version: int = 0) -> str:
    if type(user_id) is not int or not 1 <= user_id <= 2_147_483_647:
        raise ValueError("Invalid user ID")
    now = datetime.now(timezone.utc)
    if type(token_version) is not int or token_version < 0:
        raise ValueError("Invalid token version")

    payload = {
        "sub": str(user_id),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        "type": "access",
        "ver": token_version,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


def decode_access_claims(token: str) -> tuple[int, int]:
    """Verify signed access tokens and return a PostgreSQL integer user ID."""
    if len(token) > 4096:
        raise jwt.InvalidTokenError("Invalid access token")
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "nbf", "type"]},
        )
        if payload["type"] != "access":
            raise jwt.InvalidTokenError("Invalid access token type")
        # Reject bools, containers and non-integer dates even if a library
        # version happens to coerce them during expiration validation.
        if any(type(payload[name]) is not int for name in ("iat", "nbf", "exp")):
            raise jwt.InvalidTokenError("Invalid token dates")
        subject = payload["sub"]
        if not isinstance(subject, str) or re.fullmatch(r"[1-9][0-9]{0,9}", subject) is None:
            raise jwt.InvalidTokenError("Invalid token subject")
        user_id = int(subject)
        if user_id > 2_147_483_647:
            raise jwt.InvalidTokenError("Invalid token subject")
        version = payload.get("ver", 0)
        if type(version) is not int or not 0 <= version <= 2_147_483_647:
            raise jwt.InvalidTokenError("Invalid token version")
        return user_id, version
    except (TypeError, ValueError, OverflowError):
        # Malformed claim values must be authentication failures, never 500s.
        raise jwt.InvalidTokenError("Invalid access token") from None


def decode_access_token(token: str) -> int:
    return decode_access_claims(token)[0]
