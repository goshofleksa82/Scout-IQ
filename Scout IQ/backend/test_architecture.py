from unittest.mock import MagicMock
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from database import get_db
from main import app


def test_configuration_repr_hides_credentials():
    assert settings.jwt_secret not in repr(settings)
    assert settings.database_url not in repr(settings)


def test_unhandled_read_database_error_is_sanitized(client, monkeypatch, caplog):
    db = MagicMock()
    db.query.side_effect = SQLAlchemyError('private-database-detail')
    def override(): yield db
    monkeypatch.setitem(app.dependency_overrides, get_db, override)
    response = client.get('/players/count')
    assert response.status_code == 500
    assert response.json() == {'detail': 'Database service unavailable'}
    assert 'private-database-detail' not in response.text + caplog.text


def test_compatibility_imports_share_model_and_dependency_identity():
    import models, auth, database, security
    from app import models as domain_models
    from app.api import auth as auth_api
    from app.core import database as core_database, security as core_security
    assert models is domain_models and auth is auth_api
    assert database is core_database and security is core_security
