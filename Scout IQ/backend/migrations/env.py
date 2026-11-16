"""Alembic environment. Import models only, without starting the API or auth."""
import os
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from models import Base
from app.core.urls import normalize_database_url

config = context.config
target_metadata = Base.metadata
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def include_object(obj, name, type_, reflected, compare_to):
    # Autogeneration must never propose dropping unrelated database tables.
    return not (type_ == "table" and reflected and compare_to is None)


def configure(**kwargs):
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        **kwargs,
    )


def run_with_connection(connection):
    configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations():
    # A caller can supply a connection so stamping and upgrading share one
    # transaction. Test connections always point to the isolated test database.
    connection = config.attributes.get("connection")
    if connection is not None:
        run_with_connection(connection)
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    database_url=normalize_database_url(database_url)

    if context.is_offline_mode():
        configure(url=database_url, literal_binds=True, dialect_opts={"paramstyle": "named"})
        with context.begin_transaction():
            context.run_migrations()
        return

    # Pass the URL directly; ConfigParser interpolation can corrupt passwords
    # containing percent signs. NullPool avoids keeping migration sessions open.
    engine = create_engine(database_url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            run_with_connection(connection)
    finally:
        engine.dispose()


run_migrations()
