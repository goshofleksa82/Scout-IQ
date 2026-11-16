from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from conftest import TEST_PASSWORD, TestingSessionLocal
from main import app
from models import RefreshSession, User
from sessions import COOKIE_NAME, token_digest


def login(client, user):
    result = client.post('/auth/login', json={'username': user.username, 'password': TEST_PASSWORD})
    assert result.status_code == 200
    return client.cookies.get(COOKIE_NAME)


def test_refresh_rotates_and_stores_only_hashes(client, viewer_user):
    original = login(client, viewer_user)
    response = client.post('/auth/refresh')
    assert response.status_code == 200
    replacement = client.cookies.get(COOKIE_NAME)
    assert replacement != original
    with TestingSessionLocal() as db:
        rows = db.scalars(select(RefreshSession)).all()
        assert len(rows) == 2
        assert {row.token_hash for row in rows} == {token_digest(original), token_digest(replacement)}
        assert all(row.token_hash not in {original, replacement} for row in rows)
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=lax' in response.headers['set-cookie']


def test_replay_revokes_rotated_descendants(client, viewer_user):
    original = login(client, viewer_user)
    assert client.post('/auth/refresh').status_code == 200
    replacement = client.cookies.get(COOKIE_NAME)
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, original)
    assert client.post('/auth/refresh').status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, replacement)
    assert client.post('/auth/refresh').status_code == 401


@pytest.mark.parametrize('case', ['expired', 'revoked', 'inactive', 'missing', 'invalid'])
def test_invalid_refresh_sessions_cannot_issue_tokens(client, viewer_user, case):
    raw = login(client, viewer_user)
    with TestingSessionLocal() as db:
        row = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_digest(raw)))
        if case == 'expired': row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        if case == 'revoked': row.revoked_at = datetime.now(timezone.utc)
        if case == 'inactive': db.get(User, viewer_user.id).is_active = False
        db.commit()
    if case in {'missing', 'invalid'}:
        client.cookies.clear()
        if case == 'invalid': client.cookies.set(COOKIE_NAME, 'invalid')
    assert client.post('/auth/refresh').status_code == 401


def test_logout_revokes_session_and_clears_cookie(client, viewer_user):
    raw = login(client, viewer_user)
    response = client.post('/auth/logout')
    assert response.status_code == 204 and response.content == b''
    assert client.cookies.get(COOKIE_NAME) is None
    client.cookies.set(COOKIE_NAME, raw)
    assert client.post('/auth/refresh').status_code == 401
    assert client.post('/auth/logout').status_code == 204


@pytest.mark.parametrize('endpoint', ['refresh', 'logout', 'login'])
def test_cross_site_session_requests_are_rejected(client, viewer_user, endpoint):
    login(client, viewer_user)
    kwargs = {'headers': {'Origin': 'https://attacker.example'}}
    if endpoint == 'login': kwargs['json'] = {'username': viewer_user.username, 'password': TEST_PASSWORD}
    assert client.post('/auth/' + endpoint, **kwargs).status_code == 403


def test_concurrent_refresh_detects_reuse(client, viewer_user):
    raw = login(client, viewer_user)
    def refresh_once(_):
        with TestClient(app) as other:
            other.cookies.set(COOKIE_NAME, raw)
            return other.post('/auth/refresh').status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(refresh_once, range(2))) == [200, 401]
    with TestingSessionLocal() as db:
        assert all(row.revoked_at is not None for row in db.scalars(select(RefreshSession)).all())


@pytest.mark.parametrize('endpoint', ['login','refresh'])
def test_password_change_race_cannot_issue_new_version_token(client, viewer_user, monkeypatch, endpoint):
    import auth
    from sqlalchemy import update
    if endpoint=='refresh': login(client,viewer_user)
    name='issue_session' if endpoint=='login' else 'rotate_session'
    original=getattr(auth,name)
    def concurrent_password_change(*args):
        result=original(*args)
        with TestingSessionLocal() as db:
            db.get(User,viewer_user.id).token_version+=1
            db.execute(update(RefreshSession).where(RefreshSession.user_id==viewer_user.id).values(revoked_at=datetime.now(timezone.utc)))
            db.commit()
        return result
    monkeypatch.setattr(auth,name,concurrent_password_change)
    response=client.post('/auth/login',json={'username':viewer_user.username,'password':TEST_PASSWORD}) if endpoint=='login' else client.post('/auth/refresh')
    assert response.status_code==200
    assert client.get('/auth/me',headers={'Authorization':'Bearer '+response.json()['access_token']}).status_code==401
