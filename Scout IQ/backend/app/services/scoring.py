from datetime import datetime,timezone
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from app.models import Player,ScoringModel
from app.services.cohorts import cohort_players,percentile_map,position_group,resolve_season
from app.services.entities import required


def create_model(db,data,user_id):
    row=ScoringModel(**data.model_dump(),created_by_id=user_id)
    try:
        db.add(row); db.commit(); db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail='A scoring model already exists for this group and version') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500,detail='Unable to create scoring model') from None


def score_player(db,player_id,season_id=None,min_minutes=450,model_id=None,data_source=None,min_peers=3):
    player=required(db,Player,player_id)
    group=position_group(player.position)
    season_id=resolve_season(db,season_id,player_id)
    result={'player_id':player_id,'season_id':season_id,'position_group':group,'min_minutes':min_minutes,'score':None,'components':[],
        'algorithm_version':'percentile-weighted-v1',
        'purpose':'Statistical decision support to combine with video, context and scouting observations.',
        'limitations':['Criteria and weights are configurable and uncalibrated.','Scores depend on the selected dataset and peer group.','Competition strength, tactical roles, injuries and unrecorded actions are not adjusted.','Goalkeeper criteria describe distribution only.']}
    if group is None: return {**result,'data_status':'unsupported_position'}
    if model_id is not None:
        model=required(db,ScoringModel,model_id)
        if model.position_group!=group: raise HTTPException(status_code=422,detail='Scoring model does not match the player position group')
    else:
        models=db.query(ScoringModel).filter(ScoringModel.position_group==group).all()
        if not models: raise HTTPException(status_code=404,detail='No scoring model configured for this position group')
        model=max(models,key=lambda item:tuple(map(int,item.version.split('.'))))
    result['model']={'id':model.id,'name':model.name,'version':model.version,'weights':model.weights,'description':model.description}
    rows=cohort_players(db,season_id,0,group,data_source)
    target=next((row for row in rows if row['player_id']==player_id),None)
    if target is None: return {**result,'data_status':'no_match_data'}
    if target['data_source'] is None: return {**result,'data_status':'source_selection_required','available_sources':target['source_names']}
    result['data_source']=target['data_source']
    if target['minutes_played']<min_minutes: return {**result,'data_status':'insufficient_minutes'}
    features=list(model.weights)
    missing=[feature for feature in features if target['metrics'][feature] is None]
    if missing: return {**result,'data_status':'missing_metrics','missing_metrics':missing}
    peers=[row for row in rows if row['data_source']==target['data_source'] and row['minutes_played']>=min_minutes and all(row['metrics'][feature] is not None for feature in features)]
    result['cohort_size']=len(peers)
    if len(peers)<min_peers: return {**result,'data_status':'insufficient_peers','required_cohort_size':min_peers}
    score=0
    for feature,weight in model.weights.items():
        percentile=percentile_map([row['metrics'][feature] for row in peers])[target['metrics'][feature]]['percentile']
        contribution=percentile*weight; score+=contribution
        result['components'].append({'metric':feature,'value':target['metrics'][feature],'weight':weight,'percentile':percentile,'contribution':round(contribution,4)})
    fingerprint={'season_id':season_id,'source':target['data_source'],'position_group':group,'min_minutes':min_minutes,
        'features':features,'rows':[{'id':row['player_id'],'values':[row['metrics'][feature] for feature in features]} for row in peers]}
    return {**result,'score':round(score,2),'data_status':'available','generated_at':datetime.now(timezone.utc),
        'cohort_fingerprint':hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest(),
        'methodology':'A weighted mean of mean-rank percentiles among complete cases in the same season, position group and source. Ties share percentiles. Required missing metrics prevent a score; weights are never silently redistributed.'}
