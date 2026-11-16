import pytest
from test_matches import match_data


@pytest.fixture
def scored_cohort(admin_client,match_data):
    for index,player in enumerate(match_data['players']):
        assert admin_client.post(f'/matches/{match_data["match"]}/player-stats',json={'player_id':player,'minutes_played':90,'goals':0,'assists':index,'tackles':2-index}).status_code==201
    payload={'name':'Synthetic criteria','version':'0.1.0','position_group':'midfielders','weights':{'assists_per_90':0.5,'tackles_per_90':0.5}}
    response=admin_client.post('/analytics/scoring-models',json=payload)
    assert response.status_code==201
    return match_data,payload,response.json()['id']


def test_scores_explain_weighting_and_are_reproducible(admin_client,scored_cohort):
    data,payload,model=scored_cohort; player=data['players'][0]
    first=admin_client.get(f'/analytics/players/{player}/score?min_minutes=0&model_id={model}').json()
    second=admin_client.get(f'/analytics/players/{player}/score?min_minutes=0&model_id={model}').json()
    assert first['score']==50 and first['cohort_size']==3
    assert sum(row['contribution'] for row in first['components'])==first['score']
    assert first['cohort_fingerprint']==second['cohort_fingerprint']
    assert first['components']==second['components']
    assert first['model']['version']=='0.1.0'


def test_new_model_versions_change_weights_without_rewriting_history(admin_client,scored_cohort):
    data,payload,original=scored_cohort; player=data['players'][0]
    response=admin_client.post('/analytics/scoring-models',json={**payload,'version':'0.2.0','weights':{'assists_per_90':0.8,'tackles_per_90':0.2}})
    assert response.status_code==201
    assert admin_client.get(f'/analytics/players/{player}/score?min_minutes=0').json()['score']==20
    assert admin_client.get(f'/analytics/players/{player}/score?min_minutes=0&model_id={original}').json()['score']==50
    assert admin_client.put(f'/analytics/scoring-models/{original}',json=payload).status_code==405


def test_missing_required_metrics_and_low_minutes_prevent_scores(admin_client,scored_cohort):
    data,payload,original=scored_cohort; player=data['players'][0]
    assert admin_client.get(f'/analytics/players/{player}/score').json()['data_status']=='insufficient_minutes'
    response=admin_client.post('/analytics/scoring-models',json={**payload,'version':'0.3.0','weights':{'progressive_actions_per_90':1.0}})
    assert response.status_code==201
    body=admin_client.get(f'/analytics/players/{player}/score?min_minutes=0').json()
    assert body['score'] is None and body['data_status']=='missing_metrics'


@pytest.mark.parametrize('changes',[{'weights':{'assists_per_90':0.4,'tackles_per_90':0.4}}, {'weights':{'goals_per_90':1.0}}, {'version':'invalid'}, {'weights':{'assists_per_90':-1.0}}])
def test_invalid_scoring_configuration(admin_client,changes):
    payload={'name':'Invalid criteria','version':'1.0.0','position_group':'midfielders','weights':{'assists_per_90':1.0},**changes}
    assert admin_client.post('/analytics/scoring-models',json=payload).status_code==422


def test_scoring_definition_writes_require_admin(client):
    assert client.post('/analytics/scoring-models',json={}).status_code==401
