import pytest
from test_watchlists import viewer_client
from conftest import TEST_PASSWORD


def test_reports_preserve_history_and_reject_stale_edits(viewer_client,seed_test_players):
    c=viewer_client;payload={'player_id':1,'title':' Initial observation ','technical':'Software-test text, not a real observation.','summary':'Initial summary'}
    created=c.post('/reports',json=payload);assert created.status_code==201;row=created.json();rid=row['id'];assert row['version']==1 and row['title']=='Initial observation'
    edit={key:value for key,value in payload.items() if key!='player_id'};edit.update(title='Revised observation',summary='New summary',expected_version=1)
    result=c.put(f'/reports/{rid}',json=edit);assert result.status_code==200 and result.json()['version']==2
    assert c.put(f'/reports/{rid}',json=edit).status_code==409
    history=c.get(f'/reports/{rid}/history?page_size=1').json();assert history['total']==2 and history['revisions'][0]['content']['summary']=='New summary'
    original=c.get(f'/reports/{rid}/history?page=2&page_size=1').json()['revisions'][0];assert original['version']==1 and original['content']['summary']=='Initial summary'
    assert c.get('/reports?player_id=1').json()['total']==1
    assert c.get('/reports?player_id=2').json()['total']==0
    assert c.delete(f'/reports/{rid}').status_code==405


def test_reports_are_private_including_history(viewer_client,admin_user,seed_test_players):
    c=viewer_client;rid=c.post('/reports',json={'player_id':1,'title':'Private'}).json()['id']
    token=c.post('/auth/login',json={'username':admin_user.username,'password':TEST_PASSWORD}).json()['access_token'];c.headers['Authorization']='Bearer '+token
    assert c.get('/reports').json()['total']==0
    assert c.get(f'/reports/{rid}').status_code==404
    assert c.get(f'/reports/{rid}/history').status_code==404
    assert c.put(f'/reports/{rid}',json={'title':'Takeover','expected_version':1}).status_code==404


@pytest.mark.parametrize('changes',[{'title':' '},{'technical':'x'*4001},{'author_id':1},{'recommendation':'invalid'},{'observed_on':'not-a-date'}])
def test_reports_validate_structured_content(viewer_client,seed_test_players,changes):
    assert viewer_client.post('/reports',json={'player_id':1,'title':'Valid',**changes}).status_code==422


def test_report_relationship_and_authentication(viewer_client):
    assert viewer_client.post('/reports',json={'player_id':999999,'title':'Unknown player'}).status_code==404
    viewer_client.headers.pop('Authorization')
    assert viewer_client.get('/reports').status_code==401
    assert viewer_client.post('/reports',json={'player_id':1,'title':'A'}).status_code==401
