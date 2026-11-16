import pytest
from conftest import TEST_PASSWORD,TestingSessionLocal
from app.models import WatchlistItem


@pytest.fixture
def viewer_client(client,viewer_user):
    result=client.post('/auth/login',json={'username':viewer_user.username,'password':TEST_PASSWORD})
    client.headers['Authorization']='Bearer '+result.json()['access_token'];return client


def test_watchlist_crud_players_and_cascade(viewer_client,seed_test_players):
    c=viewer_client
    created=c.post('/watchlists',json={'name':' Summer targets ','description':'Private shortlist'})
    assert created.status_code==201;row=created.json();wid=row['id'];assert row['name']=='Summer targets'
    assert 'user_id' not in row
    assert c.post(f'/watchlists/{wid}/players',json={'player_id':1}).status_code==201
    assert c.post(f'/watchlists/{wid}/players',json={'player_id':1}).status_code==409
    assert c.post(f'/watchlists/{wid}/players',json={'player_id':999999}).status_code==404
    assert c.get(f'/watchlists/{wid}/players').json()['players'][0]['id']==1
    assert c.get('/watchlists').json()['watchlists'][0]['player_count']==1
    assert c.put(f'/watchlists/{wid}',json={'name':'Revised targets'}).json()['name']=='Revised targets'
    assert c.delete(f'/watchlists/{wid}/players/1').status_code==204
    assert c.delete(f'/watchlists/{wid}/players/1').status_code==204
    assert c.post(f'/watchlists/{wid}/players',json={'player_id':2}).status_code==201
    assert c.delete(f'/watchlists/{wid}').status_code==204
    assert c.get(f'/watchlists/{wid}').status_code==404
    with TestingSessionLocal() as db: assert db.query(WatchlistItem).count()==0
    assert c.get('/players').json()['total']==3


def test_private_watchlists_are_hidden_even_from_admin(viewer_client,admin_user,seed_test_players):
    c=viewer_client;wid=c.post('/watchlists',json={'name':'Private'}).json()['id']
    token=c.post('/auth/login',json={'username':admin_user.username,'password':TEST_PASSWORD}).json()['access_token'];c.headers['Authorization']='Bearer '+token
    assert c.get('/watchlists').json()['total']==0
    for method,path,payload in [('get',f'/watchlists/{wid}',None),('get',f'/watchlists/{wid}/players',None),('put',f'/watchlists/{wid}',{'name':'Takeover'}),('post',f'/watchlists/{wid}/players',{'player_id':1}),('delete',f'/watchlists/{wid}/players/1',None),('delete',f'/watchlists/{wid}',None)]:
        result=getattr(c,method)(path,**({'json':payload} if payload is not None else {}));assert result.status_code==404


def test_watchlist_validation_uniqueness_and_pagination(viewer_client):
    c=viewer_client
    for payload in [{'name':'   '},{'name':'A','user_id':1},{'name':'x'*101}]: assert c.post('/watchlists',json=payload).status_code==422
    assert c.post('/watchlists',json={'name':'A'}).status_code==201
    assert c.post('/watchlists',json={'name':'a'}).status_code==409
    assert c.post('/watchlists',json={'name':'B'}).status_code==201
    second=c.get('/watchlists?page=2&page_size=1').json();assert second['total']==2 and len(second['watchlists'])==1
    assert c.get('/watchlists?page=0').status_code==422


def test_watchlists_require_authentication(client):
    for method,path in [('get','/watchlists'),('post','/watchlists'),('get','/watchlists/1/players'),('delete','/watchlists/1')]: assert getattr(client,method)(path).status_code==401
