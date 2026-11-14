"""Pytest fixtures for ScoutIQ. WARNING: drops ORM tables in scoutiq_test."""
import os
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from models import Base, Player

load_dotenv()
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


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope='function')
def setup_test_database():
    # Destructive by design: only use an empty, disposable scoutiq_test database.
    Base.metadata.create_all(bind=test_engine)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=test_engine)


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
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
