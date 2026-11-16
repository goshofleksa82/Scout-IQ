"""Pytest fixtures for ScoutIQ. WARNING: drops ORM tables in scoutiq_test."""
import os
import secrets
import pytest
from pathlib import Path
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).with_name('.env'))
# Tokens minted by tests cannot be used against the development application.
os.environ['JWT_SECRET_KEY'] = secrets.token_urlsafe(48)

from database import get_db, engine as development_engine
from main import app
from models import Base, Player, User
from auth import get_current_user
from security import hash_password

TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
if not TEST_DATABASE_URL:
    raise RuntimeError('Set TEST_DATABASE_URL in .env before running tests')
test_url = make_url(TEST_DATABASE_URL)
if test_url.get_backend_name() != 'postgresql' or test_url.database != 'scoutiq_test':
    raise RuntimeError('TEST_DATABASE_URL must target PostgreSQL database scoutiq_test')
if DATABASE_URL and test_url.set(password=None) == make_url(DATABASE_URL).set(password=None):
    raise RuntimeError('Development and test database URLs must differ')

test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope='session', autouse=True)
def forbid_development_database_connections():
    def blocked(*args, **kwargs):
        raise RuntimeError('Tests must not connect to the development database')
    event.listen(development_engine, 'do_connect', blocked)
    event.listen(development_engine, 'checkout', blocked)
    try:
        yield
    finally:
        event.remove(development_engine, 'do_connect', blocked)
        event.remove(development_engine, 'checkout', blocked)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope='session')
def initialized_test_schema():
    # Destructive by design: only use an empty, disposable scoutiq_test database.
    with test_engine.connect() as connection:
        from sqlalchemy import text
        if connection.scalar(text('SELECT current_database()')) != 'scoutiq_test':
            raise RuntimeError('Refusing to modify a database other than scoutiq_test')
    with test_engine.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public'))
    Base.metadata.create_all(bind=test_engine)
    from app.core.audit_sql import install_audit_triggers
    with test_engine.begin() as connection:
        install_audit_triggers(lambda sql:connection.execute(text(sql)),include_beta=True)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope='function')
def setup_test_database(initialized_test_schema):
    from sqlalchemy import text
    def reset():
        with test_engine.begin() as connection:
            if connection.scalar(text('SELECT current_database()')) != 'scoutiq_test':
                raise RuntimeError('Refusing to reset a non-test database')
            connection.execute(text("SELECT set_config('scoutiq.test_cleanup','on',true)"))
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
    reset()
    try:
        yield
    finally:
        reset()


@pytest.fixture(scope='function')
def seed_test_players(setup_test_database):
    db = TestingSessionLocal()
    try:
        db.add_all([
            Player(id=1, name='Erling Haaland', age=26, position='ST', club='Manchester City', goals=20, assists=5, minutes_played=1800),
            Player(id=2, name='Lionel Messi', age=38, position='CAM', club='Inter Miami', goals=18, assists=9, minutes_played=1750),
            Player(id=3, name='Nicolo Barella', age=28, position='CM', club='Inter Milan', goals=8, assists=9, minutes_played=1890),
        ])
        db.commit()
        # Seed IDs are explicit; keep subsequent generated player IDs above them.
        from sqlalchemy import text
        db.execute(text("SELECT setval(pg_get_serial_sequence('players','id'), (SELECT max(id) FROM players), true)"))
        db.commit()
        yield
    finally:
        db.close()


@pytest.fixture(scope='function')
def zero_minute_player(seed_test_players):
    db = TestingSessionLocal()
    try:
        db.add(Player(id=4, name='Zero Minutes', age=22, position='ST', club='Test FC', goals=0, assists=0, minutes_played=0))
        db.commit()
        yield
    finally:
        db.close()


@pytest.fixture(scope='function')
def client(setup_test_database):
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


TEST_PASSWORD = 'ScoutIQ-test-password-42!'


@pytest.fixture(scope='session')
def test_password_hash():
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def admin_user(setup_test_database, test_password_hash):
    with TestingSessionLocal() as db:
        user = User(username='test_admin', email='admin@example.com', hashed_password=test_password_hash, role='admin')
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def viewer_user(setup_test_database, test_password_hash):
    with TestingSessionLocal() as db:
        user = User(username='test_viewer', email='viewer@example.com', hashed_password=test_password_hash, role='viewer')
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def admin_client(client, admin_user):
    response = client.post('/auth/login', json={'username': admin_user.username, 'password': TEST_PASSWORD})
    assert response.status_code == 200
    client.headers['Authorization'] = 'Bearer ' + response.json()['access_token']
    return client


@pytest.fixture
def authenticated_admin_for_database_failure(admin_user):
    # Only endpoint failure simulations replace get_db with a faulting mock.
    # Keep their authorization separate; normal CRUD/permission tests use JWTs.
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        yield
    finally:
        if original is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = original
