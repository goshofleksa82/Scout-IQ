import pytest


@pytest.fixture
def match_data(admin_client):
    competition = admin_client.post('/competitions',json={'name':'Synthetic Demo League'}).json()['id']
    season = admin_client.post('/seasons',json={'name':'Synthetic 2026','starts_on':'2026-01-01','ends_on':'2026-12-31'}).json()['id']
    clubs = [admin_client.post('/clubs',json={'name':name}).json()['id'] for name in ('Synthetic Home','Synthetic Away')]
    players=[]
    for index, club in enumerate([clubs[0],clubs[0],clubs[1]]):
        response = admin_client.post('/players',json={'name':f'Synthetic Player {index}','age':22,'position':'CM','club':'Synthetic Home' if index<2 else 'Synthetic Away','club_id':club,'goals':0,'assists':0,'minutes_played':0})
        player=response.json()['id']; players.append(player)
        assert admin_client.post(f'/players/{player}/memberships',json={'club_id':club,'season_id':season,'joined_on':'2026-01-01'}).status_code==201
    payload={'home_club_id':clubs[0],'away_club_id':clubs[1],'competition_id':competition,'season_id':season,'kickoff_at':'2026-05-01T15:00:00Z','status':'finished'}
    response=admin_client.post('/matches',json=payload)
    assert response.status_code==201
    match=response.json()['id']
    for index,player in enumerate(players):
        assert admin_client.post(f'/matches/{match}/participants',json={'player_id':player,'club_id':clubs[0] if index<2 else clubs[1]}).status_code==201
    return {'match':match,'clubs':clubs,'players':players,'payload':payload,'season':season}


def test_match_events_and_statistics(admin_client, match_data):
    match=match_data['match']; first,second,away=match_data['players']
    goal=admin_client.post(f'/matches/{match}/events',json={'player_id':first,'event_type':'goal','minute':30})
    assert goal.status_code==201
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':second,'event_type':'assist','minute':30,'related_goal_id':goal.json()['id']}).status_code==201
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':away,'event_type':'yellow_card','minute':90,'added_time':3}).status_code==201
    stats=admin_client.get(f'/matches/{match}/stats').json()
    assert stats['home']['goal']==1 and stats['home']['assist']==1 and stats['away']['yellow_card']==1
    assert len(admin_client.get(f'/matches/{match}/events').json())==3
    assert admin_client.get('/matches?page_size=1').json()['total']==1


def test_event_validation_and_participation(admin_client, match_data):
    match=match_data['match']; player=match_data['players'][0]
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':player,'event_type':'goal','minute':91}).status_code==400
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':999,'event_type':'goal','minute':10}).status_code==400
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':player,'event_type':'assist','minute':10}).status_code==422
    assert admin_client.post(f'/matches/{match}/participants',json={'player_id':player,'club_id':match_data['clubs'][0]}).status_code==409


def test_match_dates_relationships_and_status(admin_client, match_data):
    payload=match_data['payload']
    assert admin_client.post('/matches',json={**payload,'away_club_id':payload['home_club_id']}).status_code==422
    assert admin_client.post('/matches',json={**payload,'competition_id':999}).status_code==404
    assert admin_client.post('/matches',json={**payload,'kickoff_at':'2025-01-01T10:00:00Z'}).status_code==400
    assert admin_client.post('/matches',json={**payload,'kickoff_at':'2026-05-01T10:00:00'}).status_code==422
    match=match_data['match']; player=match_data['players'][0]
    assert admin_client.patch(f'/matches/{match}',json={'status':'scheduled'}).status_code==200
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':player,'event_type':'goal','minute':10}).status_code==400


def test_match_writes_require_authentication(client):
    assert client.get('/matches').status_code==200
    assert client.post('/matches',json={}).status_code==401
