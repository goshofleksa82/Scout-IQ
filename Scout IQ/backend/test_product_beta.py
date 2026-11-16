from datetime import datetime,timedelta,timezone
from conftest import TestingSessionLocal,TEST_PASSWORD
from test_watchlists import viewer_client
from app.models import ProductEvent,BetaFeedback,AuditLog


def test_analytics_is_opt_in_deduplicated_and_withdrawal_erases_events(viewer_client):
    c=viewer_client
    assert c.get('/product/preferences').json()['analytics_opt_in'] is False
    assert c.post('/product/events',json={'event':'comparison_opened'}).status_code==204
    with TestingSessionLocal() as db: assert db.query(ProductEvent).count()==0
    prefs=c.patch('/product/preferences',json={'analytics_opt_in':True,'onboarding_completed':True}).json();assert prefs['onboarding_completed_at']
    for _ in range(2): assert c.post('/product/events',json={'event':'comparison_opened'}).status_code==204
    with TestingSessionLocal() as db: assert db.query(ProductEvent).count()==1
    assert c.patch('/product/preferences',json={'analytics_opt_in':False}).status_code==200
    with TestingSessionLocal() as db: assert db.query(ProductEvent).count()==0
    assert c.post('/product/events',json={'event':'unknown','query':'private search'}).status_code==422
    assert c.patch('/product/preferences',json={'analytics_opt_in':True,'role':'admin'}).status_code==422


def test_feedback_is_structured_private_and_admin_reviewed(viewer_client,admin_user):
    c=viewer_client;payload={'category':'usability','area':'comparison','rating':3,'message':'Software-test feedback only. Not a real beta response.'}
    created=c.post('/feedback',json=payload);assert created.status_code==201;fid=created.json()['id']
    assert c.get('/feedback').json()['total']==1
    assert c.get('/admin/feedback').status_code==403
    assert c.patch(f'/admin/feedback/{fid}',json={'status':'planned','priority':'high'}).status_code==403
    token=c.post('/auth/login',json={'username':admin_user.username,'password':TEST_PASSWORD}).json()['access_token'];c.headers['Authorization']='Bearer '+token
    assert c.get('/feedback').json()['total']==0
    assert c.get('/admin/feedback').json()['total']==1
    reviewed=c.patch(f'/admin/feedback/{fid}',json={'status':'planned','priority':'high','admin_note':'Private triage note'});assert reviewed.status_code==200 and reviewed.json()['priority']=='high'
    with TestingSessionLocal() as db:
        audit=str([(r.before,r.after) for r in db.query(AuditLog).filter(AuditLog.entity=='beta_feedback')]);assert payload['message'] not in audit and 'Private triage note' not in audit


def test_feedback_validation_and_product_permissions(viewer_client):
    c=viewer_client
    for payload in [{'category':'bug','area':'search','rating':6,'message':'A valid description'},{'category':'bug','area':'search','rating':3,'message':'short'},{'category':'bug','area':'search','rating':3,'message':'A valid description','author_id':1}]: assert c.post('/feedback',json=payload).status_code==422
    c.headers.pop('Authorization');assert c.get('/product/preferences').status_code==401 and c.post('/feedback',json={}).status_code==401


def test_beta_metrics_are_observed_counts_and_admin_only(admin_client):
    body=admin_client.get('/admin/product-metrics').json()
    assert body['events']==[] and body['feedback_statuses']=={} and body['analytics_opted_in']==0
