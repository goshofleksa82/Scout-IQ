"""Interpretable metrics from complete, season-compatible match aggregates."""
from app.services.statistics import aggregate_statistics

METRIC_DEFINITIONS={
    'goals_per_90':'Goals × 90 / recorded minutes',
    'assists_per_90':'Assists × 90 / recorded minutes',
    'goal_contributions_per_90':'(Goals + assists) × 90 / recorded minutes',
    'shots_per_90':'Shots × 90 / recorded minutes',
    'tackles_per_90':'Tackles × 90 / recorded minutes',
    'passes_completed_per_90':'Completed passes × 90 / recorded minutes',
    'pass_completion_pct':'Completed passes × 100 / attempted passes',
    'goal_conversion_pct':'Goals × 100 / shots',
    'progressive_actions_per_90':'(Recorded progressive passes + carries) × 90 / recorded minutes',
}


def ratio(numerator,denominator,multiplier=1):
    if numerator is None or denominator is None or denominator<=0: return None
    return round(numerator*multiplier/denominator,2)


def add_known(a,b): return None if a is None or b is None else a+b


def metrics_from_totals(totals):
    minutes=totals.get('minutes_played')
    return {
        'goals_per_90':ratio(totals.get('goals'),minutes,90),
        'assists_per_90':ratio(totals.get('assists'),minutes,90),
        'goal_contributions_per_90':ratio(add_known(totals.get('goals'),totals.get('assists')),minutes,90),
        'shots_per_90':ratio(totals.get('shots'),minutes,90),
        'tackles_per_90':ratio(totals.get('tackles'),minutes,90),
        'passes_completed_per_90':ratio(totals.get('passes_completed'),minutes,90),
        'pass_completion_pct':ratio(totals.get('passes_completed'),totals.get('passes_attempted'),100),
        'goal_conversion_pct':ratio(totals.get('goals'),totals.get('shots'),100),
        'progressive_actions_per_90':ratio(add_known(totals.get('progressive_passes'),totals.get('progressive_carries')),minutes,90),
    }


def advanced_metrics(db,player_id,season_id=None,data_source=None):
    result=aggregate_statistics(db,player_id,season_id,data_source)
    result['metrics']=metrics_from_totals(result['totals'])
    if len(result['data_sources'])>1:
        result['metrics']['progressive_actions_per_90']=None
    result['definitions']=METRIC_DEFINITIONS
    result['methodology']='Finished matches only; two decimal places. A metric with missing inputs or a zero denominator is unavailable, not zero.'
    return result
