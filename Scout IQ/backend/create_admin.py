"""Trusted local administrator provisioning; never exposed as an API route."""
import argparse
import getpass
import sys
import warnings

from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User
from schemas import UserCreate
from security import hash_password


class AdminSetupError(RuntimeError):
    pass


def create_admin(data: UserCreate, db: Session) -> User:
    """Create a new admin; refuse duplicate accounts rather than promote users."""
    try:
        existing = db.query(User).filter(or_(
            User.username == data.username,
            User.email == str(data.email),
        )).first()
        if existing is not None:
            raise AdminSetupError("Username or email already registered; no account was changed")
        try:
            hashed_password = hash_password(data.password.get_secret_value())
        except Exception:
            raise AdminSetupError("Unable to hash password; no account was created") from None
        user = User(
            username=data.username,
            email=str(data.email),
            hashed_password=hashed_password,
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise AdminSetupError("Username or email already registered; no account was changed") from None
    except SQLAlchemyError:
        db.rollback()
        raise AdminSetupError("Unable to create administrator; check database configuration and migrations") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create a ScoutIQ administrator using a hidden password prompt")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    # getpass otherwise falls back to an echoed prompt in unsupported consoles.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Administrator password (12–128 characters): ")
            confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            print("Passwords do not match; no account was created", file=sys.stderr)
            return 1
        data = UserCreate(username=args.username, email=args.email, password=password)
        del password, confirmation
        with SessionLocal() as db:
            user = create_admin(data, db)
        print(f"Administrator '{user.username}' created (id {user.id})")
        return 0
    except ValidationError as exc:
        # Never print the ValidationError itself: it may contain password input.
        fields = sorted({str(error["loc"][0]) for error in exc.errors()})
        print("Invalid account details: " + ", ".join(fields), file=sys.stderr)
        return 1
    except AdminSetupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        print("Administrator setup cancelled; use a terminal with hidden password input", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
