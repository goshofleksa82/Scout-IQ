"""Controlled admin setup, using the isolated PostgreSQL test database."""
import getpass
import warnings
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import create_admin as provision
from conftest import TEST_PASSWORD, TestingSessionLocal
from models import User
from schemas import UserCreate
from security import verify_password


@pytest.fixture
def admin_details():
    return UserCreate(username='  LOCAL_ADMIN  ', email='OWNER@EXAMPLE.COM', password=TEST_PASSWORD)


def test_create_admin_uses_hashed_password_and_explicit_role(setup_test_database, admin_details):
    with TestingSessionLocal() as db:
        user = provision.create_admin(admin_details, db)
        assert user.username == 'local_admin'
        assert user.email == 'owner@example.com'
        assert user.role == 'admin'
        assert user.is_active is True
        assert user.hashed_password.startswith('$argon2id$')
        assert verify_password(TEST_PASSWORD, user.hashed_password)


@pytest.mark.parametrize('duplicate', ['username', 'email'])
def test_admin_setup_refuses_duplicate_viewer_and_does_not_promote(viewer_user, duplicate):
    data = UserCreate(
        username=viewer_user.username if duplicate == 'username' else 'different_admin',
        email=viewer_user.email if duplicate == 'email' else 'different@example.com',
        password=TEST_PASSWORD,
    )
    with TestingSessionLocal() as db:
        with pytest.raises(provision.AdminSetupError, match='already registered'):
            provision.create_admin(data, db)
        assert db.get(User, viewer_user.id).role == 'viewer'
        assert db.query(User).count() == 1


@pytest.mark.parametrize('stage', ['lookup', 'commit', 'race'])
def test_admin_setup_database_failures_roll_back_and_hide_details(admin_details, stage):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    if stage == 'lookup':
        db.query.side_effect = SQLAlchemyError('private-database-detail')
    elif stage == 'commit':
        db.commit.side_effect = SQLAlchemyError('private-database-detail')
    else:
        db.commit.side_effect = IntegrityError('insert users', {}, Exception('private-database-detail'))
    with pytest.raises(provision.AdminSetupError) as caught:
        provision.create_admin(admin_details, db)
    db.rollback.assert_called_once()
    assert 'private-database-detail' not in str(caught.value)


def test_admin_cli_prompts_twice_and_creates_login_capable_admin(client, monkeypatch, capsys):
    prompts = MagicMock(side_effect=[TEST_PASSWORD, TEST_PASSWORD])
    monkeypatch.setattr(provision.getpass, 'getpass', prompts)
    monkeypatch.setattr(provision, 'SessionLocal', TestingSessionLocal)
    assert provision.main(['--username', 'Local_Admin', '--email', 'owner@example.com']) == 0
    assert prompts.call_count == 2
    output = capsys.readouterr()
    assert TEST_PASSWORD not in output.out + output.err
    login = client.post('/auth/login', json={'username': 'local_admin', 'password': TEST_PASSWORD})
    assert login.status_code == 200
    response = client.get('/auth/me', headers={'Authorization': 'Bearer ' + login.json()['access_token']})
    assert response.json()['role'] == 'admin'


@pytest.mark.parametrize('passwords', [(TEST_PASSWORD, 'mismatch'), ('short', 'short')])
def test_admin_cli_rejects_invalid_password_without_opening_database(monkeypatch, capsys, passwords):
    monkeypatch.setattr(provision.getpass, 'getpass', MagicMock(side_effect=passwords))
    session = MagicMock()
    monkeypatch.setattr(provision, 'SessionLocal', session)
    assert provision.main(['--username', 'local_admin', '--email', 'owner@example.com']) == 1
    session.assert_not_called()
    output = capsys.readouterr()
    assert TEST_PASSWORD not in output.out + output.err


def test_admin_cli_refuses_password_echo_fallback(monkeypatch, capsys):
    def unavailable(prompt):
        warnings.warn('Password may be echoed', getpass.GetPassWarning)
        pytest.fail('The password prompt fell back to echoed input')
    monkeypatch.setattr(provision.getpass, 'getpass', unavailable)
    session = MagicMock()
    monkeypatch.setattr(provision, 'SessionLocal', session)
    assert provision.main(['--username', 'local_admin', '--email', 'owner@example.com']) == 1
    session.assert_not_called()
    assert 'hidden password input' in capsys.readouterr().err


def test_admin_cli_database_error_is_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(provision.getpass, 'getpass', MagicMock(side_effect=[TEST_PASSWORD, TEST_PASSWORD]))
    db = MagicMock()
    db.query.side_effect = SQLAlchemyError('private-database-detail')
    session = MagicMock()
    session.return_value.__enter__.return_value = db
    monkeypatch.setattr(provision, 'SessionLocal', session)
    assert provision.main(['--username', 'local_admin', '--email', 'owner@example.com']) == 1
    output = capsys.readouterr()
    assert 'private-database-detail' not in output.out + output.err
    assert TEST_PASSWORD not in output.out + output.err
    db.rollback.assert_called_once()
