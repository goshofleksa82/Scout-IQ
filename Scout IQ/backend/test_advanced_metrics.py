import pytest
from app.services.advanced_metrics import metrics_from_totals
from test_matches import match_data


def test_interpretable_metric_formulas_and_rounding():
    values=metrics_from_totals({'minutes_played':180,'goals':3,'assists':1,'shots':10,'tackles':5,'passes_completed':90,'passes_attempted':120,'progressive_passes':4,'progressive_carries':2})
    assert values=={'goals_per_90':1.5,'assists_per_90':0.5,'goal_contributions_per_90':2.0,'shots_per_90':5.0,'tackles_per_90':2.5,'passes_completed_per_90':45.0,'pass_completion_pct':75.0,'goal_conversion_pct':30.0,'progressive_actions_per_90':3.0}
    assert metrics_from_totals({'minutes_played':270,'goals':1})['goals_per_90']==0.33


def test_missing_data_and_zero_denominators_are_not_imputed():
    assert all(value is None for value in metrics_from_totals({}).values())
    values=metrics_from_totals({'minutes_played':0,'goals':0,'shots':0,'passes_completed':0,'passes_attempted':0})
    assert values['goals_per_90'] is None and values['goal_conversion_pct'] is None and values['pass_completion_pct'] is None
    assert metrics_from_totals({'minutes_played':90,'progressive_passes':2})['progressive_actions_per_90'] is None


def test_season_specific_advanced_metrics_api(admin_client,match_data):
    player=match_data['players'][0]; match=match_data['match']; season=match_data['season']
    assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':1,'assists':0,'shots':4,'tackles':2,'passes_attempted':50,'passes_completed':40}).status_code==201
    response=admin_client.get(f'/analytics/players/{player}/metrics?season_id={season}')
    assert response.status_code==200
    body=response.json()
    assert body['metrics']['shots_per_90']==4 and body['metrics']['pass_completion_pct']==80
    assert body['metrics']['progressive_actions_per_90'] is None
    assert body['season_id']==season and body['source']=='player_match_stats'
