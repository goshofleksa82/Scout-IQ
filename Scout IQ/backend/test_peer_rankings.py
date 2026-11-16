from app.services.cohorts import percentile_map
from test_matches import match_data


def test_ties_and_singleton_percentiles():
    assert percentile_map([1,1,0])=={0:{'rank':3,'percentile':0.0},1:{'rank':1,'percentile':75.0}}
    assert percentile_map([1])[1]['percentile'] is None
    assert percentile_map([1,1])[1]['percentile']==50


def test_position_peer_ranking_thresholds_and_ties(admin_client,match_data):
    match=match_data['match']; players=match_data['players']
    for index,player in enumerate(players):
        assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':0,'assists':1 if index<2 else 0}).status_code==201
    response=admin_client.get('/analytics/rankings',params={'position_group':'midfielders','metric':'assists_per_90','season_id':match_data['season'],'min_minutes':0})
    assert response.status_code==200
    body=response.json()
    assert [row['rank'] for row in body['rankings']]==[1,1,3]
    assert [row['percentile'] for row in body['rankings']]==[75,75,0]
    assert admin_client.get('/analytics/rankings?position_group=midfielders&min_minutes=180').json()['rankings']==[]
    assert admin_client.get('/analytics/rankings?position_group=strikers&min_minutes=0').json()['rankings']==[]


def test_unsupported_position_metrics_are_rejected(client):
    assert client.get('/analytics/rankings?position_group=goalkeepers&metric=goals_per_90').status_code==422


def test_singleton_peer_group_does_not_claim_a_percentile(admin_client,match_data):
    assert admin_client.post(f'/matches/{match_data["match"]}/player-stats',json={'player_id':match_data['players'][0],'minutes_played':90,'goals':0,'assists':0}).status_code==201
    body=admin_client.get('/analytics/rankings?position_group=midfielders&min_minutes=0').json()
    assert body['peer_count']==1 and body['rankings'][0]['percentile'] is None


def test_provider_cohorts_require_selection_and_exclude_mixed_player_sources(admin_client,match_data):
    from test_imports import upload
    player=match_data['players'][0]; match=match_data['match']
    assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':0,'assists':1}).status_code==201
    second=admin_client.post('/matches',json={**match_data['payload'],'kickoff_at':'2026-05-02T15:00:00Z'}).json()['id']
    assert admin_client.post(f'/matches/{second}/participants',json={'player_id':player,'club_id':match_data['clubs'][0]}).status_code==201
    csv=f'external_id,player_id,match_id,minutes_played,goals,assists\nmixed-source,{player},{second},90,0,1\n'
    assert upload(admin_client,csv,kind='player-stats').status_code==200
    result=admin_client.get('/analytics/rankings?position_group=midfielders&min_minutes=0').json()
    assert result['rankings']==[]
    assert result['data_status']=='source_selection_required'
    selected=admin_client.get('/analytics/rankings?position_group=midfielders&min_minutes=0&data_source=manual').json()
    assert selected['peer_count']==1
    assert admin_client.get(f'/players/{player}/match-stats').json()['data_sources']==['manual','synthetic fixture']
