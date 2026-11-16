import pytest
from test_matches import match_data


def test_stats_aggregate_and_duplicate_prevention(admin_client,match_data):
    match=match_data['match']; player=match_data['players'][0]
    payload={'player_id':player,'minutes_played':90,'goals':2,'assists':1,'shots':4,'passes_attempted':50,'passes_completed':40,'tackles':3}
    assert admin_client.post(f'/matches/{match}/player-stats',json=payload).status_code==201
    assert admin_client.post(f'/matches/{match}/player-stats',json=payload).status_code==409
    aggregate=admin_client.get(f'/players/{player}/match-stats?season_id={match_data["season"]}').json()
    assert aggregate['totals']['goals']==2 and aggregate['totals']['minutes_played']==90
    assert aggregate['matches_recorded']==1 and aggregate['matches_played']==1
    assert aggregate['totals']['progressive_passes'] is None
    assert admin_client.get(f'/players/{player}').json()['goals']==0


@pytest.mark.parametrize('changes',[{'minutes_played':-1},{'goals':5,'shots':1},{'passes_attempted':3,'passes_completed':4},{'minutes_played':0,'goals':1}])
def test_statistical_consistency(admin_client,match_data,changes):
    payload={'player_id':match_data['players'][0],'minutes_played':90,'goals':0,'assists':0,**changes}
    assert admin_client.post(f'/matches/{match_data["match"]}/player-stats',json=payload).status_code==422


def test_zero_minutes_and_missing_data_are_explicit(admin_client,match_data):
    player=match_data['players'][0]; match=match_data['match']
    empty=admin_client.get(f'/players/{player}/match-stats').json()
    assert empty['data_status']=='no_data' and empty['totals']['goals'] is None
    assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':0,'goals':0,'assists':0}).status_code==201
    totals=admin_client.get(f'/players/{player}/match-stats').json()
    assert totals['matches_played']==0 and totals['totals']['minutes_played']==0


def test_statistics_cannot_contradict_recorded_events(admin_client,match_data):
    player=match_data['players'][0]; match=match_data['match']
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':player,'event_type':'goal','minute':10}).status_code==201
    assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':0,'assists':0}).status_code==400


def test_new_events_cannot_exceed_existing_statistics(admin_client,match_data):
    player=match_data['players'][0]; match=match_data['match']
    assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':0,'assists':0}).status_code==201
    assert admin_client.post(f'/matches/{match}/events',json={'player_id':player,'event_type':'goal','minute':10}).status_code==400
