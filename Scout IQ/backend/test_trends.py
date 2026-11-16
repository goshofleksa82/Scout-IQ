from app.services.trends import rolling_values, window_metric, compare_windows
from test_matches import match_data


def sample(goals,minutes=90): return {'goals':goals,'minutes_played':minutes}


def test_rolling_rates_weight_minutes_and_preserve_missing_samples():
    assert rolling_values([sample(0),sample(1),sample(2)],'goals_per_90',2,2)==[None,0.5,1.5]
    assert window_metric([sample(1,90),sample(1,30)],'goals_per_90')==1.5
    assert rolling_values([{'minutes_played':90,'shots':None},{'minutes_played':90,'shots':2}],'shots_per_90',2,2)==[None,None]


def test_exploratory_changes_are_deterministic_and_sample_limited():
    rows=[sample(0) for _ in range(5)]+[sample(1) for _ in range(5)]
    result=compare_windows(rows,'goals_per_90',5)
    assert result['signal']=='increase' and result['p_value']<0.05
    assert result==compare_windows(rows,'goals_per_90',5)
    assert compare_windows(rows[:3],'goals_per_90',2)['data_status']=='insufficient_sample'
    assert compare_windows([sample(0)]*10,'goals_per_90',5)['signal'] is None


def test_trends_are_chronological_and_show_season_context(admin_client,match_data):
    player=match_data['players'][0]
    entries=[(match_data['match'],0)]
    for day,goals in [(3,2),(2,1)]:
        match=admin_client.post('/matches',json={**match_data['payload'],'kickoff_at':f'2026-05-{day:02}T15:00:00Z'}).json()['id']
        assert admin_client.post(f'/matches/{match}/participants',json={'player_id':player,'club_id':match_data['clubs'][0]}).status_code==201
        entries.append((match,goals))
    for match,goals in entries:
        assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':goals,'assists':0}).status_code==201
    response=admin_client.get(f'/analytics/players/{player}/trends?window=2&min_samples=2')
    assert response.status_code==200
    body=response.json()
    assert [row['value'] for row in body['observations']]==[0,1,2]
    assert [row['rolling_average'] for row in body['observations']]==[None,0.5,1.5]
    assert body['season_comparisons'][0]['value']==1
    assert body['comparison']['data_status']=='insufficient_sample'


def test_invalid_trend_configuration(client,seed_test_players):
    assert client.get('/analytics/players/1/trends?window=2&min_samples=3').status_code==422
    assert client.get('/analytics/players/1/trends?metric=unknown').status_code==422
