import pytest
from conftest import TEST_PASSWORD, TestingSessionLocal
from models import User, RefreshSession
from security import create_access_token
from sessions import COOKIE_NAME


def headers(user):
    return {'Authorization': 'Bearer ' + create_access_token(user.id, user.token_version)}


def test_profile_updates_only_current_user(client, viewer_user, admin_user):
    response = client.patch('/users/me', json={'username': ' NEW_NAME ', 'email': 'NEW@EXAMPLE.COM'}, headers=headers(viewer_user))
    assert response.status_code == 200
    assert response.json()['username'] == 'new_name'
    assert response.json()['email'] == 'new@example.com'
    assert response.json()['role'] == 'viewer'
    with TestingSessionLocal() as db:
        assert db.get(User, admin_user.id).username == 'test_admin'
    assert client.patch(f'/users/{admin_user.id}', json={'username': 'hijack'}, headers=headers(viewer_user)).status_code == 404


@pytest.mark.parametrize('field', ['username', 'email'])
def test_duplicate_profile_fields_are_409(client, viewer_user, admin_user, field):
    response = client.patch('/users/me', json={field: getattr(admin_user, field).upper()}, headers=headers(viewer_user))
    assert response.status_code == 409
    with TestingSessionLocal() as db:
        assert db.get(User, viewer_user.id).username == 'test_viewer'


@pytest.mark.parametrize('body', [{'role': 'admin'}, {'id': 2}, {'is_active': False}, {'username': None}, {'username': ' a '}, {'email': 'bad'}])
def test_profile_validation_and_privilege_fields(client, viewer_user, body):
    assert client.patch('/users/me', json=body, headers=headers(viewer_user)).status_code == 422


def test_account_endpoints_require_authentication(client):
    assert client.patch('/users/me', json={'username': 'new_scout'}).status_code == 401
    assert client.post('/users/me/change-password', json={'current_password': TEST_PASSWORD, 'new_password': 'changed-password-42'}).status_code == 401


def test_password_change_revokes_all_refresh_and_access_tokens(client, viewer_user):
    assert client.post('/auth/login', json={'username': viewer_user.username, 'password': TEST_PASSWORD}).status_code == 200
    refresh = client.cookies.get(COOKIE_NAME)
    old_headers = headers(viewer_user)
    response = client.post('/users/me/change-password', json={'current_password': TEST_PASSWORD, 'new_password': 'changed-password-42'}, headers=old_headers)
    assert response.status_code == 204
    assert client.get('/auth/me', headers=old_headers).status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, refresh)
    assert client.post('/auth/refresh').status_code == 401
    assert client.post('/auth/login', json={'username': viewer_user.username, 'password': TEST_PASSWORD}).status_code == 401
    login = client.post('/auth/login', json={'username': viewer_user.username, 'password': 'changed-password-42'})
    assert login.status_code == 200
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + login.json()['access_token']}).status_code == 200
    with TestingSessionLocal() as db:
        assert db.get(User, viewer_user.id).token_version == 1


def test_wrong_current_password_leaves_sessions_valid(client, viewer_user):
    auth = headers(viewer_user)
    response = client.post('/users/me/change-password', json={'current_password': 'incorrect-password', 'new_password': 'changed-password-42'}, headers=auth)
    assert response.status_code == 400
    assert client.get('/auth/me', headers=auth).status_code == 200


def test_password_validation_never_echoes_secrets(client, viewer_user):
    response = client.post('/users/me/change-password', json={'current_password': TEST_PASSWORD, 'new_password': 'pw-7!'}, headers=headers(viewer_user))
    assert response.status_code == 422
    assert TEST_PASSWORD not in response.text and 'pw-7!' not in response.text
