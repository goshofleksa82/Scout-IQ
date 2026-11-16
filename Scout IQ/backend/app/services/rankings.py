from fastapi import HTTPException
from app.services.cohorts import POSITION_GROUPS, POSITION_METRICS, cohort_players, percentile_map, resolve_season


def rank_peers(db,group,metric,season_id,min_minutes,source=None):
    metric=metric or POSITION_METRICS[group][0]
    if metric not in POSITION_METRICS[group]:
        raise HTTPException(status_code=422,detail='Metric is not supported for this position group')
    season_id=resolve_season(db,season_id)
    all_players=cohort_players(db,season_id,min_minutes,group,source)
    sources=sorted({provider for row in all_players for provider in row['source_names']})
    selected=source.strip().lower() if source is not None else (sources[0] if len(sources)==1 else None)
    result={'season_id':season_id,'position_group':group,'metric':metric,'min_minutes':min_minutes,
        'data_source':selected,'available_sources':sources,'rankings':[],
        'methodology':'Within the same season, position group and provider. Published two-decimal metrics determine competition ranks and mean-rank percentiles. Ties share ranks; a singleton has no percentile.',
        'limitations':'Position groups and rate metrics do not adjust for tactics, opposition or competition strength. Goalkeeper metrics cover distribution only.'}
    if len(sources)>1 and selected is None:
        return {**result,'data_status':'source_selection_required','peer_count':0}
    players=[row for row in all_players if selected is not None and row['data_source']==selected and row['metrics'][metric] is not None]
    percentiles=percentile_map([row['metrics'][metric] for row in players])
    for row in sorted(players,key=lambda row:(-row['metrics'][metric],row['player_id'])):
        value=row['metrics'][metric]
        result['rankings'].append({'player_id':row['player_id'],'name':row['name'],'position':row['position'],
            'value':value,'minutes_played':row['minutes_played'],**percentiles[value]})
    return {**result,'peer_count':len(players),'data_status':'available' if players else 'no_eligible_data'}
