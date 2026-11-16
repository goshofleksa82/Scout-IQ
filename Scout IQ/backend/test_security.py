"""Password, token configuration, and credential-redaction checks."""
from pathlib import Path
import runpy

import pytest

from conftest import TEST_PASSWORD
from schemas import UserCreate
from security import create_access_token, decode_access_token, hash_password, verify_password


def test_argon2id_hashes_are_salted_and_verify():
    first = hash_password(TEST_PASSWORD)
    second = hash_password(TEST_PASSWORD)
    assert first.startswith('$argon2id$') and second.startswith('$argon2id$')
    assert first != second
    assert TEST_PASSWORD not in first
    assert verify_password(TEST_PASSWORD, first)
    assert not verify_password('incorrect-password', first)


def test_password_spaces_are_preserved():
    value = '  correct password with spaces  '
    user = UserCreate(username='scout', email='scout@example.com', password=value)
    stored = hash_password(user.password.get_secret_value())
    assert verify_password(value, stored)
    assert not verify_password(value.strip(), stored)
    assert value not in repr(user)
    assert value not in user.model_dump_json()


@pytest.mark.parametrize('user_id', [1, 2_147_483_647])
def test_valid_integer_subject_round_trip(user_id):
    assert decode_access_token(create_access_token(user_id)) == user_id


@pytest.mark.parametrize('user_id', [0, -1, 2_147_483_648, '1', True, None])
def test_token_creation_rejects_invalid_user_ids(user_id):
    with pytest.raises(ValueError):
        create_access_token(user_id)


@pytest.mark.parametrize('settings,message', [
    ({'JWT_SECRET_KEY': ''}, 'JWT_SECRET_KEY'),
    ({'JWT_SECRET_KEY': 'too-short'}, 'JWT_SECRET_KEY'),
    ({'JWT_ALGORITHM': 'none'}, 'Unsupported JWT algorithm'),
    ({'JWT_ALGORITHM': 'HS512'}, 'Unsupported JWT algorithm'),
    ({'ACCESS_TOKEN_EXPIRE_MINUTES': '0'}, 'Invalid token expiration'),
    ({'ACCESS_TOKEN_EXPIRE_MINUTES': '1441'}, 'Invalid token expiration'),
    ({'ACCESS_TOKEN_EXPIRE_MINUTES': 'invalid'}, 'Invalid token expiration'),
])
def test_invalid_security_configuration_fails_closed(monkeypatch, settings, message):
    import dotenv
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *args, **kwargs: False)
    monkeypatch.setenv('JWT_ALGORITHM', 'HS256')
    monkeypatch.setenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30')
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match=message):
        from app.core.config import load_settings
        load_settings()


def test_development_database_connections_are_blocked():
    from database import engine
    with pytest.raises(RuntimeError, match='Tests must not connect'):
        with engine.connect():
            pytest.fail('A test connected to development')
