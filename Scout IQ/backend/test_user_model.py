"""User constraints are exercised against PostgreSQL, never the development DB."""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, DataError

from conftest import TestingSessionLocal, test_engine
from models import User


@pytest.fixture
def connection(setup_test_database):
    with test_engine.begin() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "scoutiq_test"
        yield connection


def insert_user(connection, **changes):
    values = {
        "username": "test_viewer",
        "email": "viewer@example.test",
        # A fixture placeholder, not a password or a usable authentication hash.
        "hashed_password": "$argon2id$test-fixture",
        **changes,
    }
    columns = ", ".join(values)
    parameters = ", ".join(f":{key}" for key in values)
    return connection.execute(
        text(f"INSERT INTO users ({columns}) VALUES ({parameters}) RETURNING id, role, is_active"),
        values,
    ).one()


def test_user_database_schema(connection):
    inspector = inspect(connection)
    columns = {column["name"]: column for column in inspector.get_columns("users")}
    assert set(columns) == {"id", "username", "email", "hashed_password", "role", "is_active", "token_version", "analytics_opt_in", "onboarding_completed_at"}
    assert columns["onboarding_completed_at"]["nullable"] is True
    assert all(not column["nullable"] for name, column in columns.items() if name != "onboarding_completed_at")
    assert inspector.get_pk_constraint("users")["constrained_columns"] == ["id"]
    assert columns["id"]["identity"]
    for name, length in (("username", 50), ("email", 255), ("hashed_password", 255), ("role", 20)):
        assert columns[name]["type"].length == length
    assert any(check["name"] == "ck_users_valid_role" for check in inspector.get_check_constraints("users"))


def test_raw_insert_gets_generated_id_and_database_defaults(connection):
    first = insert_user(connection)
    second = insert_user(connection, username="second", email="second@example.test")
    assert first.id > 0
    assert second.id > first.id
    assert (first.role, first.is_active) == ("viewer", True)


def test_orm_insert_gets_defaults(setup_test_database):
    with TestingSessionLocal() as session:
        user = User(username="orm_viewer", email="orm@example.test", hashed_password="$argon2id$test-fixture")
        session.add(user)
        session.commit()
        session.refresh(user)
        assert user.id > 0
        assert user.role == "viewer"
        assert user.is_active is True
        assert user.analytics_opt_in is False
        assert user.onboarding_completed_at is None


@pytest.mark.parametrize("role", ["viewer", "admin"])
def test_database_accepts_supported_roles(connection, role):
    assert insert_user(connection, role=role).role == role


@pytest.mark.parametrize("role", ["superuser", "ADMIN", ""])
def test_database_rejects_unsupported_roles(connection, role):
    with pytest.raises(IntegrityError), connection.begin_nested():
        insert_user(connection, role=role)


@pytest.mark.parametrize("field", ["username", "email"])
def test_database_rejects_duplicate_identity(connection, field):
    insert_user(connection)
    changes = {"username": "second", "email": "second@example.test"}
    changes[field] = "test_viewer" if field == "username" else "viewer@example.test"
    with pytest.raises(IntegrityError), connection.begin_nested():
        insert_user(connection, **changes)


@pytest.mark.parametrize("field", ["username", "email", "hashed_password", "role", "is_active"])
def test_database_rejects_explicit_null(connection, field):
    with pytest.raises(IntegrityError), connection.begin_nested():
        insert_user(connection, **{field: None})


@pytest.mark.parametrize("field,length", [("username", 51), ("email", 256), ("hashed_password", 256)])
def test_database_enforces_string_lengths(connection, field, length):
    with pytest.raises(DataError), connection.begin_nested():
        insert_user(connection, **{field: "x" * length})


def test_user_can_be_inactive(connection):
    assert insert_user(connection, is_active=False).is_active is False
