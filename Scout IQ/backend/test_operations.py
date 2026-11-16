from dataclasses import replace
from unittest.mock import MagicMock
import json,logging
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import get_db
from app.core.operations import SafeJSONFormatter
from app.core.urls import normalize_database_url
from app.main import create_app


def test_health_headers_host_validation_and_cors(client):
    response=client.get('/health/live');assert response.json()=={'status':'ok'}
    assert len(response.headers['x-request-id'])==32 and response.headers['cache-control']=='no-store'
    assert client.get('/health/live',headers={'Host':'untrusted.example'}).status_code==400
    trusted=client.options('/players',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET'})
    assert trusted.headers['access-control-allow-origin']=='http://localhost:5173'
    assert 'access-control-allow-origin' not in client.get('/players',headers={'Origin':'https://untrusted.example'}).headers


def test_readiness_checks_migration_revision_and_sanitizes_database_failures(client,monkeypatch):
    db=MagicMock();db.scalar.return_value='wrong-revision'
    def override(): yield db
    monkeypatch.setitem(client.app.dependency_overrides,get_db,override)
    assert client.get('/health/ready').status_code==503
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    db.scalar.return_value=ScriptDirectory.from_config(Config('alembic.ini')).get_current_head()
    assert client.get('/health/ready').json()=={'status':'ready'}
    db.execute.side_effect=SQLAlchemyError('private-db-password')
    result=client.get('/health/ready');assert result.status_code==503 and 'private' not in result.text


def test_monitoring_never_records_raw_paths_queries_or_tokens(client,caplog):
    with caplog.at_level(logging.INFO,logger='scoutiq.http'): client.get('/unknown-sensitive-name?token=private-query-value',headers={'Authorization':'Bearer private-access-token'})
    assert 'private-query-value' not in caplog.text and 'private-access-token' not in caplog.text and 'unknown-sensitive-name' not in caplog.text


def test_hosted_https_configuration(monkeypatch):
    from app import main
    monkeypatch.setattr(main,'settings',replace(main.settings,enforce_https=True,environment='staging',allowed_hosts=('testserver',)))
    app=create_app()
    with TestClient(app,base_url='http://testserver',follow_redirects=False) as c: assert c.get('/health/live').status_code==307
    with TestClient(app,base_url='https://testserver') as c: assert 'max-age' in c.get('/health/live').headers['strict-transport-security']


def test_url_normalization_and_log_exception_redaction():
    assert normalize_database_url('postgres://user:secret@db/scoutiq')=='postgresql+psycopg://user:secret@db/scoutiq'
    record=logging.LogRecord('example',logging.ERROR,'',1,'Operation failed',(),(ValueError,ValueError('private-body'),None))
    result=SafeJSONFormatter().format(record);assert 'private-body' not in result and json.loads(result)['error_type']=='ValueError'
