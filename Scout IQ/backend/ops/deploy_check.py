"""Run after migration and after a rollout. No credentials or private rows printed."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings
from app.core.audit_sql import CURRENT_AUDIT_TABLES

config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
config.set_main_option('script_location',str(Path(__file__).resolve().parents[1]/'migrations'))
with engine.connect() as connection:
    config.attributes['connection']=connection
    command.check(config)
    triggers=connection.scalar(text("SELECT count(*) FROM information_schema.triggers WHERE trigger_name='scoutiq_audit_row' AND event_manipulation='INSERT' AND event_object_schema=current_schema()"))
    if triggers!=len(CURRENT_AUDIT_TABLES): raise RuntimeError('Audit capture is incomplete')
    if settings.environment in {'staging','production'}:
        from app.services.sessions import COOKIE_SECURE
        assert COOKIE_SECURE and all(o.startswith('https://') for o in settings.allowed_origins)
print('Deployment schema, audit triggers and environment checks passed.')
