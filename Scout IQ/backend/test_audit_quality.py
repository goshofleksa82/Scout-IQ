import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from conftest import TestingSessionLocal
from test_watchlists import viewer_client
from test_imports import upload
from app.models import AuditLog,Player
from test_matches import match_data


def test_transactional_audit_captures_create_update_delete_and_actor(admin_client,admin_user):
    c=admin_client;payload={'name':'Synthetic audited identity','age':22,'position':'ST','club':'Synthetic audit club','goals':0,'assists':0,'minutes_played':0}
    player=c.post('/players',json=payload).json()['id']
    assert c.patch(f'/players/{player}',json={'goals':1}).status_code==200
    assert c.delete(f'/players/{player}').status_code==204
    rows=c.get(f'/admin/audit?entity=players&record_id={player}').json()['events']
    assert [r['action'] for r in rows]==['delete','update','create']
    assert all(r['actor_id']==admin_user.id for r in rows)
    assert rows[1]['before']['goals']==0 and rows[1]['after']['goals']==1
    assert rows[0]['after'] is None
    assert c.get('/admin/audit?entity=clubs').json()['total']==1


def test_bulk_import_is_audited_and_idempotent_import_does_not_repeat_players(admin_client):
    first=upload(admin_client);assert first.status_code==200
    assert upload(admin_client).status_code==200
    events=admin_client.get('/admin/audit?entity=players').json()['events']
    assert len(events)==2 and all(e['action']=='create' for e in events)


def test_failed_mutation_rolls_back_its_audit(admin_client):
    with TestingSessionLocal() as db:
        before=db.query(AuditLog).count()
        db.add(Player(name='Rollback test',age=22,position='ST',club='Rollback club',goals=0,assists=0,minutes_played=0));db.flush()
        assert db.query(AuditLog).count()>before
        db.rollback()
    with TestingSessionLocal() as db: assert db.query(AuditLog).count()==before


def test_audit_redacts_account_and_private_report_content(viewer_client,seed_test_players):
    c=viewer_client
    report=c.post('/reports',json={'player_id':1,'title':'Private title','technical':'Confidential observation'});assert report.status_code==201
    assert c.patch('/users/me',json={'email':'private-contact@example.com'}).status_code==200
    with TestingSessionLocal() as db:
        content=str([(r.before,r.after) for r in db.query(AuditLog).all()])
        for secret in ['Confidential observation','Private title','private-contact@example.com','hashed_password','test_viewer','content']:
            assert secret not in content


def test_audit_records_are_append_only_in_database(admin_client):
    with TestingSessionLocal() as db:
        assert db.query(AuditLog).count()>0
        with pytest.raises(DBAPIError): db.execute(text("UPDATE audit_logs SET source='tampered'"));db.commit()
        db.rollback()
        with pytest.raises(DBAPIError): db.execute(text('DELETE FROM audit_logs'));db.commit()
        db.rollback()


def test_quality_checks_record_missing_evidence_without_modifying_players(admin_client,seed_test_players):
    c=admin_client;before=c.get('/players').json()
    preview=c.get('/admin/data-quality');assert preview.status_code==200
    body=preview.json();assert body['error_count']==0
    assert next(r for r in body['checks'] if r['code']=='player_provenance')['affected']==3
    run=c.post('/admin/data-quality/runs');assert run.status_code==201
    assert c.get('/admin/data-quality/runs').json()['total']==1
    assert c.get('/players').json()==before


def test_audit_and_quality_are_admin_only_and_have_no_mutation_routes(viewer_client):
    for path in ['/admin/audit','/admin/data-quality','/admin/data-quality/runs']: assert viewer_client.get(path).status_code==403
    assert viewer_client.post('/admin/data-quality/runs').status_code==403
    assert viewer_client.delete('/admin/audit/1').status_code in (404,405)


def test_quality_detects_direct_database_date_inconsistency(admin_client,match_data):
    with TestingSessionLocal() as db:
        db.execute(text("UPDATE matches SET kickoff_at='2025-01-01T15:00:00Z' WHERE id=:id"),{'id':match_data['match']});db.commit()
    result=admin_client.get('/admin/data-quality').json()
    assert next(c for c in result['checks'] if c['code']=='match_season_dates')['affected']==1
    assert next(c for c in result['checks'] if c['code']=='roster_membership')['affected']==3
    assert result['error_count']>=4
