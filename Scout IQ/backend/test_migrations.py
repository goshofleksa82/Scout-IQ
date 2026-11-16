"""Rehearse migrations in a disposable schema inside scoutiq_test."""
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from conftest import test_engine
from models import Base

BASELINE = "20261116_0001"
CONFIG_PATH = Path(__file__).resolve().with_name("alembic.ini")
HEAD = ScriptDirectory.from_config(Config(str(CONFIG_PATH))).get_current_head()


@pytest.fixture
def migration_db():
    # The schema and every DDL/data change disappear when this transaction rolls
    # back. No public tables or configured development database are touched.
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "scoutiq_test"
            schema = "scoutiq_migration_test_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            connection.info['migration_schema'] = schema
            config = Config(str(CONFIG_PATH))
            config.attributes["connection"] = connection
            yield connection, config
        finally:
            transaction.rollback()


def player_snapshot(connection):
    rows = connection.execute(text("SELECT id,name,age,position,club,goals,assists,minutes_played FROM players ORDER BY id")).all()
    inspector = inspect(connection)
    columns = [
        (column["name"], str(column["type"]), column["nullable"], column.get("identity"))
        for column in inspector.get_columns("players")
        if column['name'] in {'id','name','age','position','club','goals','assists','minutes_played'}
    ]
    checks = inspector.get_check_constraints("players")
    # Resolve by OID to avoid including the disposable schema's name.
    sequence = connection.scalar(text("SELECT pg_get_serial_sequence('players', 'id')"))
    state = connection.execute(text(f"SELECT last_value, is_called FROM {sequence}")).one()
    return rows, columns, checks, state


def add_player(connection):
    connection.execute(text(
        "INSERT INTO players (name, age, position, club, goals, assists, minutes_played) "
        "VALUES ('Preserved Player', 25, 'CM', 'Test FC', 3, 4, 900)"
    ))


def test_empty_database_upgrade_matches_models(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    assert set(inspect(connection).get_table_names(schema=connection.info['migration_schema'])) == set(Base.metadata.tables) | {"alembic_version"}
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == HEAD
    command.check(config)
    command.upgrade(config, "head")  # Already-current databases are a no-op.


def test_existing_players_survive_stamp_upgrade_and_users_rollback(migration_db):
    connection, config = migration_db
    # Simulate the actual legacy schema: players exist without Alembic history.
    command.upgrade(config, BASELINE)
    add_player(connection)
    connection.execute(text("DROP TABLE alembic_version"))
    before = player_snapshot(connection)

    command.stamp(config, BASELINE)
    command.upgrade(config, "head")
    assert player_snapshot(connection) == before
    command.check(config)

    # Users created by the migration have defaults even with raw SQL.
    row = connection.execute(text(
        "INSERT INTO users (username, email, hashed_password) "
        "VALUES ('migration_viewer', 'migration@example.test', '$argon2id$test-fixture') "
        "RETURNING id, role, is_active"
    )).one()
    assert row.id > 0
    assert (row.role, row.is_active) == ("viewer", True)

    command.downgrade(config, BASELINE)
    assert "users" not in inspect(connection).get_table_names(schema=connection.info['migration_schema'])
    assert player_snapshot(connection) == before
    command.upgrade(config, "head")
    assert player_snapshot(connection) == before


def test_baseline_refuses_to_drop_players(migration_db):
    connection, config = migration_db
    command.upgrade(config, BASELINE)
    add_player(connection)
    before = player_snapshot(connection)
    with pytest.raises(RuntimeError, match="player data must be preserved"):
        command.downgrade(config, "base")
    assert player_snapshot(connection) == before


def test_autogeneration_leaves_unmanaged_tables_alone(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    connection.execute(text("CREATE TABLE unrelated_data (id integer PRIMARY KEY)"))
    command.check(config)
    assert "unrelated_data" in inspect(connection).get_table_names()


def test_users_upgrade_sql_contains_no_player_mutation():
    buffer = StringIO()
    config = Config(str(CONFIG_PATH), output_buffer=buffer)
    command.upgrade(config, f"{BASELINE}:20261116_0002", sql=True)
    sql = buffer.getvalue().lower()
    assert "create table users" in sql
    assert "ck_users_valid_role" in sql
    for mutation in ("drop table players", "alter table players", "create table players", "delete from players", "update players", "insert into players", "setval"):
        assert mutation not in sql


def test_legacy_player_clubs_are_backfilled(migration_db):
    connection, config = migration_db
    command.upgrade(config, '20261116_0005')
    add_player(connection)
    command.upgrade(config, 'head')
    row = connection.execute(text('SELECT p.club, c.name, c.country FROM players p JOIN clubs c ON p.club_id=c.id')).one()
    assert tuple(row) == ('Test FC', 'Test FC', None)
    assert next(c for c in inspect(connection).get_columns('players') if c['name']=='club_id')['nullable'] is False


def test_audit_migrations_do_not_require_future_tables_or_touch_other_schemas(migration_db):
    connection,config=migration_db
    command.upgrade(config,'20261116_0014')
    schema=connection.info['migration_schema']
    assert 'beta_feedback' not in inspect(connection).get_table_names(schema=schema)
    assert connection.scalar(text("SELECT count(*) FROM information_schema.triggers WHERE event_object_schema=:schema AND trigger_name='scoutiq_audit_row' AND event_manipulation='INSERT'"),{'schema':schema})==18
    command.upgrade(config,'head')
    assert connection.scalar(text("SELECT count(*) FROM information_schema.triggers WHERE event_object_schema=:schema AND trigger_name='scoutiq_audit_row' AND event_manipulation='INSERT'"),{'schema':schema})==19
