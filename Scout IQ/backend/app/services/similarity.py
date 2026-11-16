import hashlib
import json
from math import sqrt
from statistics import fmean, pstdev
from fastapi import HTTPException
from app.models import Player
from app.services.entities import required
from app.services.cohorts import POSITION_METRICS, cohort_players, position_group, resolve_season

DEFAULT_FEATURES={
    'strikers':('goals_per_90','assists_per_90','shots_per_90','goal_conversion_pct'),
    'wingers':('goals_per_90','assists_per_90','shots_per_90'),
    'midfielders':('assists_per_90','tackles_per_90','pass_completion_pct'),
    'defenders':('tackles_per_90','pass_completion_pct','passes_completed_per_90'),
    'goalkeepers':('pass_completion_pct','passes_completed_per_90'),
}


def normalized_similarity(rows,target_id,features,limit=5):
    parameters={feature:{'mean':fmean(row['metrics'][feature] for row in rows),
                         'std_dev':pstdev(row['metrics'][feature] for row in rows)} for feature in features}
    def vector(row):
        return [(row['metrics'][feature]-parameters[feature]['mean'])/parameters[feature]['std_dev']
                if parameters[feature]['std_dev']>0 else 0.0 for feature in features]
    target=next(row for row in rows if row['player_id']==target_id)
    reference=vector(target); results=[]
    for row in rows:
        if row['player_id']==target_id: continue
        distance=sqrt(fmean((a-b)**2 for a,b in zip(reference,vector(row))))
        results.append({'player_id':row['player_id'],'name':row.get('name'),'position':row.get('position'),
            'minutes_played':row.get('minutes_played'),'similarity':round(100/(1+distance),2),
            'distance':round(distance,6),'metrics':{feature:row['metrics'][feature] for feature in features}})
    results.sort(key=lambda row:(row['distance'],row['player_id']))
    fingerprint=hashlib.sha256(json.dumps([{'id':row['player_id'],'values':[row['metrics'][feature] for feature in features]} for row in sorted(rows,key=lambda row:row['player_id'])],sort_keys=True).encode()).hexdigest()
    return {'similar':results[:limit],'normalization':parameters,'cohort_fingerprint':fingerprint,
            'constant_features':[feature for feature,param in parameters.items() if param['std_dev']==0]}


def similar_players(db,player_id,season_id=None,min_minutes=450,limit=5,features=None,data_source=None):
    player=required(db,Player,player_id)
    group=position_group(player.position)
    season_id=resolve_season(db,season_id,player_id)
    result={'player_id':player_id,'season_id':season_id,'position_group':group,'min_minutes':min_minutes,'similar':[],
        'methodology':'Complete cases from one season, position group and source. Two-decimal metric inputs use population z-scores; constant dimensions contribute zero. Similarity = 100 / (1 + root-mean-square standardized distance).',
        'limitations':'Equal metric weights and correlated features influence results. The measure describes this dataset; combine it with video, role and competition context.'}
    if group is None: return {**result,'data_status':'unsupported_position'}
    selected=list(DEFAULT_FEATURES[group]) if features is None else [name.strip() for name in features.split(',')]
    if not 2<=len(selected)<=5 or len(set(selected))!=len(selected) or any(name not in POSITION_METRICS[group] for name in selected):
        raise HTTPException(status_code=422,detail='Select 2–5 distinct metrics supported for this position group')
    result['features']=selected
    rows=cohort_players(db,season_id,0,group,data_source)
    target=next((row for row in rows if row['player_id']==player_id),None)
    if target is None: return {**result,'data_status':'no_match_data'}
    if target['data_source'] is None:
        return {**result,'data_status':'source_selection_required','available_sources':target['source_names']}
    source=target['data_source']; result['data_source']=source
    if target['minutes_played']<min_minutes: return {**result,'data_status':'insufficient_minutes'}
    missing=[feature for feature in selected if target['metrics'][feature] is None]
    if missing: return {**result,'data_status':'missing_metrics','missing_metrics':missing}
    candidates=[row for row in rows if row['data_source']==source and row['minutes_played']>=min_minutes and all(row['metrics'][feature] is not None for feature in selected)]
    if len(candidates)<2: return {**result,'data_status':'insufficient_peers','peer_count':0}
    return {**result,**normalized_similarity(candidates,player_id,selected,limit),'peer_count':len(candidates)-1,'data_status':'available'}
