import hashlib,json
import pytest
from pathlib import Path
from app.schemas.statistics import StatsValues
from ops.load_demo import load_demo,DEMO_DIR
from conftest import test_engine,TEST_DATABASE_URL
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from app.models import Player,User,ImportBatch


def test_licensed_demo_has_verified_provenance_and_no_invented_optional_metrics():
    raw=(DEMO_DIR/'world-cup-2018.json').read_bytes();manifest=json.loads((DEMO_DIR/'manifest.json').read_text());data=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()==manifest['dataset_sha256']
    assert data['license']=='CC BY 4.0' and data['age_as_of']=='2018-07-15'
    assert len(data['players'])==42 and len(data['matches'])==13 and len(data['statistics'])==195
    assert manifest['validation']['known_source_goal_fields_matched']
    for row in data['statistics']:
        StatsValues.model_validate({k:row[k] for k in StatsValues.model_fields})
        assert row['tackles'] is None and row['progressive_passes'] is None and row['progressive_carries'] is None
    assert len(data['omitted'])==2


@pytest.mark.parametrize('name',['scoutiq','scoutiq_staging','production','neondb'])
def test_demo_loader_refuses_existing_application_database_names(name):
    with pytest.raises(RuntimeError,match='separate empty'): load_demo('postgresql+psycopg://unused:unused@localhost/'+name,'unused')


def test_licensed_demo_load_is_atomic_and_never_overwrites_existing_rows(setup_test_database,tmp_path,monkeypatch):
    schema='scoutiq_demo_test_'+uuid4().hex[:8]
    root=Path(__file__).resolve().parent
    with test_engine.begin() as conn:
        assert conn.scalar(text('SELECT current_database()'))=='scoutiq_test'
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}",public'))
        config=Config(str(root/'alembic.ini'));config.attributes['connection']=conn
        command.upgrade(config,'head')
        conn.execute(text("INSERT INTO users(username,email,hashed_password,role) VALUES ('demo_test_operator','operator@example.com','unusable-software-fixture','admin')"))
    url=make_url(TEST_DATABASE_URL).update_query_dict({'options':'-csearch_path='+schema+',public'})
    engine=create_engine(url)
    try:
        data=json.loads((DEMO_DIR/'world-cup-2018.json').read_bytes());data['statistics'][0]['goals']=999
        raw=json.dumps(data).encode();(tmp_path/'world-cup-2018.json').write_bytes(raw)
        manifest=json.loads((DEMO_DIR/'manifest.json').read_text());manifest['dataset_sha256']=hashlib.sha256(raw).hexdigest();(tmp_path/'manifest.json').write_text(json.dumps(manifest))
        import ops.load_demo as loader
        with monkeypatch.context() as scoped:
            scoped.setattr(loader,'DEMO_DIR',tmp_path)
            with pytest.raises(ValueError):load_demo(TEST_DATABASE_URL,'demo_test_operator',schema)
        with Session(engine) as db: assert db.query(Player).count()==0 and db.query(ImportBatch).count()==0
        counts=load_demo(TEST_DATABASE_URL,'demo_test_operator',schema);assert counts['players']==42 and counts['statistics']==195
        with Session(engine) as db:
            mbappe=db.query(Player).filter(Player.name.startswith('Kylian Mbapp')).one();assert mbappe.goals==4 and mbappe.age==19
            before=[(p.id,p.name,p.goals,p.assists,p.minutes_played) for p in db.query(Player).order_by(Player.id)]
            from app.services.data_quality import run_checks
            assert run_checks(db)['error_count']==0
        with pytest.raises(RuntimeError,match='never overwritten'):load_demo(TEST_DATABASE_URL,'demo_test_operator',schema)
        with Session(engine) as db: assert [(p.id,p.name,p.goals,p.assists,p.minutes_played) for p in db.query(Player).order_by(Player.id)]==before
    finally:
        engine.dispose()
        with test_engine.begin() as conn:
            assert conn.scalar(text('SELECT current_database()'))=='scoutiq_test'
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
