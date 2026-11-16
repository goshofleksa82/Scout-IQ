"""Authentication and real JWT permission checks, using scoutiq_test only."""
from datetime import datetime, timedelta, timezone
import secrets
from unittest.mock import MagicMock

import jwt
import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import auth
from conftest import TEST_PASSWORD, TestingSessionLocal
from database import get_db
from main import app
from models import Player, User
from security import JWT_ALGORITHM, JWT_SECRET_KEY, create_access_token, verify_password


@pytest.fixture
def registration():
    return {"username": "new_scout", "email": "scout@example.com", "password": TEST_PASSWORD}


def headers_for(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


def signed_claims(user_id, changes=None, remove=()):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "nbf": now, "exp": now + timedelta(minutes=10), "type": "access"}
    payload.update(changes or {})
    for key in remove:
        payload.pop(key, None)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def test_register_viewer_hashes_password_and_excludes_secrets(client, registration):
    response = client.post('/auth/register', json=registration)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {'id', 'username', 'email', 'role', 'is_active'}
    assert body['role'] == 'viewer'
    assert body['is_active'] is True
    with TestingSessionLocal() as db:
        user = db.get(User, body['id'])
        assert user.hashed_password.startswith('$argon2id$')
        assert user.hashed_password != TEST_PASSWORD
        assert verify_password(TEST_PASSWORD, user.hashed_password)
    assert TEST_PASSWORD not in response.text


def test_registration_normalizes_username_and_email(client, registration):
    registration.update(username='  Mixed_Scout  ', email='  Scout@EXAMPLE.COM  ')
    response = client.post('/auth/register', json=registration)
    assert response.status_code == 201
    assert response.json()['username'] == 'mixed_scout'
    assert response.json()['email'] == 'scout@example.com'


@pytest.mark.parametrize('field', ['username', 'email'])
def test_duplicate_registration_is_rejected_including_case(client, registration, field):
    assert client.post('/auth/register', json=registration).status_code == 201
    second = {**registration, 'username': 'different_scout', 'email': 'different@example.com'}
    second[field] = registration[field].upper()
    response = client.post('/auth/register', json=second)
    assert response.status_code == 409
    with TestingSessionLocal() as db:
        assert db.query(User).count() == 1


@pytest.mark.parametrize('extra', [{'role': 'admin'}, {'role': 'viewer'}, {'is_active': False}, {'hashed_password': 'supplied'}, {'id': 1}])
def test_public_registration_cannot_set_privileged_fields(client, registration, extra):
    response = client.post('/auth/register', json={**registration, **extra})
    assert response.status_code == 422
    assert TEST_PASSWORD not in response.text
    with TestingSessionLocal() as db:
        assert db.query(User).count() == 0


@pytest.mark.parametrize('changes', [
    {'username': '  a  '}, {'username': 'a' * 51}, {'username': 'bad name'},
    {'username': 'scouté'}, {'username': ''}, {'username': None},
    {'email': 'invalid'}, {'email': None},
    {'password': 'too-short'}, {'password': 'x' * 129},
    {'password': ' ' * 12}, {'password': None}, {'password': {'secret': 'nested-password'}},
])
def test_invalid_registration_is_rejected_without_echoing_input(client, registration, changes):
    response = client.post('/auth/register', json={**registration, **changes})
    assert response.status_code == 422
    assert TEST_PASSWORD not in response.text
    assert 'too-short' not in response.text
    assert 'nested-password' not in response.text
    assert all('input' not in error and 'ctx' not in error for error in response.json()['detail'])


def test_malformed_auth_body_does_not_echo_nested_password(client):
    response = client.post('/auth/register', json=[{'password': 'private-nested-password'}])
    assert response.status_code == 422
    assert 'private-nested-password' not in response.text


def test_successful_login_returns_signed_token_and_me(client, viewer_user):
    response = client.post('/auth/login', json={'username': '  TEST_VIEWER  ', 'password': TEST_PASSWORD})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['pragma'] == 'no-cache'
    body = response.json()
    assert set(body) == {'access_token', 'token_type'}
    assert body['token_type'] == 'bearer'
    payload = jwt.decode(body['access_token'], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert payload['sub'] == str(viewer_user.id)
    assert payload['type'] == 'access'
    assert payload['exp'] > payload['iat']
    me = client.get('/auth/me', headers={'Authorization': 'Bearer ' + body['access_token']})
    assert me.status_code == 200
    assert me.json() == {'id': viewer_user.id, 'username': viewer_user.username, 'email': viewer_user.email, 'role': 'viewer', 'is_active': True}
    assert 'hashed_password' not in me.text and TEST_PASSWORD not in me.text


@pytest.mark.parametrize('username,password', [('test_viewer', 'wrong-password'), ('no_such_user', TEST_PASSWORD)])
def test_incorrect_credentials_are_rejected(client, viewer_user, username, password):
    response = client.post('/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    assert response.json()['detail'] == 'Invalid or expired authentication credentials'
    assert password not in response.text


def test_unknown_user_still_performs_password_verification(client, monkeypatch):
    verify = MagicMock(wraps=auth.verify_password)
    monkeypatch.setattr(auth, 'verify_password', verify)
    response = client.post('/auth/login', json={'username': 'no_such_user', 'password': TEST_PASSWORD})
    assert response.status_code == 401
    verify.assert_called_once_with(TEST_PASSWORD, auth.DUMMY_PASSWORD_HASH)


@pytest.mark.parametrize('body', [
    {'username': 'test_viewer', 'password': 'x' * 129},
    {'username': 'test_viewer', 'password': None},
    {'username': 'test_viewer', 'password': TEST_PASSWORD, 'role': 'admin'},
])
def test_login_validation_does_not_echo_passwords(client, body):
    response = client.post('/auth/login', json=body)
    assert response.status_code == 422
    assert TEST_PASSWORD not in response.text
    assert 'x' * 129 not in response.text


@pytest.mark.parametrize('authorization', [None, 'Basic abc', 'Bearer', 'Bearer invalid-token'])
def test_me_rejects_missing_or_malformed_credentials(client, authorization):
    response = client.get('/auth/me', headers={} if authorization is None else {'Authorization': authorization})
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'


@pytest.mark.parametrize('claim', ['sub', 'exp', 'iat', 'nbf', 'type'])
def test_required_token_claims_cannot_be_omitted(client, viewer_user, claim):
    token = signed_claims(viewer_user.id, remove=(claim,))
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


@pytest.mark.parametrize('subject', ['0', '-1', '01', '2147483648', '9' * 5000, '١', '²', '1.0', 1, None, [], {}, True])
def test_invalid_subjects_are_401_not_database_errors(client, viewer_user, subject):
    token = signed_claims(viewer_user.id, {'sub': subject})
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


@pytest.mark.parametrize('claim', ['iat', 'nbf', 'exp'])
@pytest.mark.parametrize('value', [None, [], {}, 'invalid-date', float('inf'), True])
def test_malformed_token_dates_are_unauthorized(client, viewer_user, claim, value):
    token = signed_claims(viewer_user.id, {claim: value})
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


@pytest.mark.parametrize('case', ['expired', 'future_nbf', 'future_iat', 'wrong_type', 'wrong_signature', 'unsigned', 'wrong_algorithm'])
def test_invalid_or_expired_tokens_are_rejected(client, viewer_user, case):
    now = datetime.now(timezone.utc)
    changes = {
        'expired': {'exp': now - timedelta(seconds=1)},
        'future_nbf': {'nbf': now + timedelta(hours=1)},
        'future_iat': {'iat': now + timedelta(hours=1)},
        'wrong_type': {'type': 'refresh'},
    }
    token = signed_claims(viewer_user.id, changes.get(case))
    if case == 'wrong_signature':
        prefix, signature = token.rsplit('.', 1)
        token = prefix + '.' + ('A' if signature[0] != 'A' else 'B') + signature[1:]
    elif case in {'unsigned', 'wrong_algorithm'}:
        payload = {'sub': str(viewer_user.id), 'iat': now, 'nbf': now, 'exp': now + timedelta(minutes=5), 'type': 'access'}
        token = jwt.encode(payload, '' if case == 'unsigned' else secrets.token_urlsafe(64), algorithm='none' if case == 'unsigned' else 'HS512')
    response = client.get('/auth/me', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401


def test_inactive_user_cannot_log_in_or_use_existing_token(client, viewer_user, seed_test_players):
    headers = headers_for(viewer_user)
    with TestingSessionLocal() as db:
        db.get(User, viewer_user.id).is_active = False
        db.commit()
    assert client.post('/auth/login', json={'username': viewer_user.username, 'password': TEST_PASSWORD}).status_code == 401
    assert client.get('/auth/me', headers=headers).status_code == 401
    assert client.patch('/players/1', json={'goals': 999}, headers=headers).status_code == 401


def test_deleted_user_token_is_rejected(client, viewer_user):
    headers = headers_for(viewer_user)
    with TestingSessionLocal() as db:
        db.delete(db.get(User, viewer_user.id))
        db.commit()
    assert client.get('/auth/me', headers=headers).status_code == 401


PLAYER = {'name': 'Test Signing', 'age': 22, 'position': 'CM', 'club': 'Test FC', 'goals': 2, 'assists': 3, 'minutes_played': 900}


@pytest.mark.parametrize('method,path,body', [('post', '/players', PLAYER), ('patch', '/players/1', {'goals': 999}), ('delete', '/players/1', None)])
@pytest.mark.parametrize('role', ['anonymous', 'viewer'])
def test_player_writes_require_an_active_administrator(client, seed_test_players, viewer_user, method, path, body, role):
    headers = {} if role == 'anonymous' else headers_for(viewer_user)
    kwargs = {'headers': headers}
    if body is not None:
        kwargs['json'] = body
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == (401 if role == 'anonymous' else 403)
    with TestingSessionLocal() as db:
        assert db.query(Player).count() == 3
        assert db.get(Player, 1).goals == 20


def test_admin_can_create_update_and_delete_players(admin_client):
    created = admin_client.post('/players', json=PLAYER)
    assert created.status_code == 201
    player_id = created.json()['id']
    updated = admin_client.patch(f'/players/{player_id}', json={'goals': 5})
    assert updated.status_code == 200 and updated.json()['goals'] == 5
    deleted = admin_client.delete(f'/players/{player_id}')
    assert deleted.status_code == 204 and deleted.content == b''
    assert admin_client.get(f'/players/{player_id}').status_code == 404


def test_demotion_takes_effect_for_existing_admin_tokens(admin_client, admin_user):
    with TestingSessionLocal() as db:
        db.get(User, admin_user.id).role = 'viewer'
        db.commit()
    assert admin_client.post('/players', json=PLAYER).status_code == 403


def test_token_role_claim_cannot_override_database_role(client, viewer_user):
    token = signed_claims(viewer_user.id, {'role': 'admin'})
    assert client.post('/players', json=PLAYER, headers={'Authorization': 'Bearer ' + token}).status_code == 403


@pytest.mark.parametrize('path', ['/', '/players', '/players/count', '/players/filter?position=ST', '/players/sort', '/players/1', '/players/1/stats', '/players/compare?player1=1&player2=2', '/players/rankings'])
def test_read_endpoints_stay_public(client, seed_test_players, path):
    assert client.get(path).status_code == 200


def override_database(monkeypatch, db):
    def override():
        yield db
    monkeypatch.setitem(app.dependency_overrides, get_db, override)


@pytest.mark.parametrize('stage', ['lookup', 'commit', 'race'])
def test_registration_database_failures_roll_back_and_hide_details(client, registration, monkeypatch, caplog, stage):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    secret = 'private-database-detail'
    if stage == 'lookup':
        db.query.side_effect = SQLAlchemyError(secret)
    elif stage == 'commit':
        db.commit.side_effect = SQLAlchemyError(secret)
    else:
        db.commit.side_effect = IntegrityError('insert into users', {}, Exception(secret))
    override_database(monkeypatch, db)
    response = client.post('/auth/register', json=registration)
    assert response.status_code == (409 if stage == 'race' else 500)
    db.rollback.assert_called_once()
    assert secret not in response.text and secret not in caplog.text
    assert TEST_PASSWORD not in response.text and TEST_PASSWORD not in caplog.text


@pytest.mark.parametrize('endpoint', ['login', 'me'])
def test_auth_lookup_database_errors_are_sanitized(client, monkeypatch, caplog, endpoint):
    db = MagicMock()
    db.query.side_effect = SQLAlchemyError('private-database-detail')
    db.get.side_effect = SQLAlchemyError('private-database-detail')
    override_database(monkeypatch, db)
    if endpoint == 'login':
        response = client.post('/auth/login', json={'username': 'test_viewer', 'password': TEST_PASSWORD})
    else:
        response = client.get('/auth/me', headers={'Authorization': 'Bearer ' + create_access_token(1)})
    assert response.status_code == 500
    db.rollback.assert_called_once()
    assert 'private-database-detail' not in response.text and 'private-database-detail' not in caplog.text


def test_corrupt_stored_hash_is_not_exposed(client, viewer_user, caplog):
    with TestingSessionLocal() as db:
        db.get(User, viewer_user.id).hashed_password = 'private-broken-hash'
        db.commit()
    response = client.post('/auth/login', json={'username': viewer_user.username, 'password': TEST_PASSWORD})
    assert response.status_code == 500
    assert 'private-broken-hash' not in response.text and 'private-broken-hash' not in caplog.text


def test_hashing_failure_is_sanitized(client, registration, monkeypatch, caplog):
    monkeypatch.setattr(auth, 'hash_password', MagicMock(side_effect=RuntimeError('private-hasher-detail')))
    response = client.post('/auth/register', json=registration)
    assert response.status_code == 500
    assert 'private-hasher-detail' not in response.text and 'private-hasher-detail' not in caplog.text
    with TestingSessionLocal() as db:
        assert db.query(User).count() == 0
