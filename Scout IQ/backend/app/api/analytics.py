from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.advanced_metrics import advanced_metrics
from typing import Literal
from app.services.rankings import rank_peers
from app.services.similarity import similar_players
from app.services.trends import performance_trends
from app.core.dependencies import require_admin
from app.models import ScoringModel,User
from app.schemas.scoring import ScoringModelCreate,ScoringModelResponse
from app.services.scoring import create_model,score_player
from app.services.entities import required
from sqlalchemy import func
from app.models import Player,PlayerMatchStats,ImportBatch,Match

router=APIRouter(prefix='/analytics',tags=['Analytics'])


@router.get('/players/{player_id}/provenance')
def provenance(player_id:int,season_id:int|None=Query(None,ge=1),db:Session=Depends(get_db)):
    player=required(db,Player,player_id)
    batch=db.get(ImportBatch,player.import_batch_id) if player.import_batch_id else None
    source=func.lower(func.coalesce(ImportBatch.source,'manual'))
    query=db.query(source,func.count(PlayerMatchStats.id),func.max(PlayerMatchStats.updated_at),ImportBatch.rights_basis).select_from(PlayerMatchStats).join(Match,Match.id==PlayerMatchStats.match_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id).filter(PlayerMatchStats.player_id==player_id,Match.status=='finished')
    if season_id is not None: query=query.filter(Match.season_id==season_id)
    rows=query.group_by(source,ImportBatch.rights_basis).order_by(source).all()
    return {'player_id':player_id,'season_id':season_id,
        'player_record':{'source':batch.source if batch else 'legacy_or_manual','imported_at':batch.created_at if batch else None,'created_at':player.created_at,'updated_at':player.updated_at,'rights_basis':batch.rights_basis if batch else None,**{key:batch.report.get(key) if batch and isinstance(batch.report,dict) else None for key in ('age_as_of','observation_window','team_context','position_context')}},
        'match_statistics':[{'source':row[0],'records':row[1],'last_updated_at':row[2],'rights_basis':row[3]} for row in rows],
        'note':'An import date is not the date of a football observation. Unknown provenance and rights remain unspecified.'}


@router.get('/players/{player_id}/metrics')
def metrics(player_id:int,season_id:int|None=Query(None,ge=1),data_source:str|None=Query(None,min_length=1,max_length=255),db:Session=Depends(get_db)):
    return advanced_metrics(db,player_id,season_id,data_source)


@router.get('/rankings')
def rankings(position_group:Literal['strikers','wingers','midfielders','defenders','goalkeepers']='strikers',
    metric:str|None=None,season_id:int|None=Query(None,ge=1),min_minutes:int=Query(450,ge=0,le=1000000),
    data_source:str|None=Query(None,min_length=1,max_length=255),db:Session=Depends(get_db)):
    return rank_peers(db,position_group,metric,season_id,min_minutes,data_source)


@router.get('/players/{player_id}/similar')
def similar(player_id:int,limit:int=Query(5,ge=1,le=20),min_minutes:int=Query(450,ge=0,le=1000000),
    season_id:int|None=Query(None,ge=1),features:str|None=Query(None,max_length=500),
    data_source:str|None=Query(None,min_length=1,max_length=255),db:Session=Depends(get_db)):
    return similar_players(db,player_id,season_id,min_minutes,limit,features,data_source)


@router.get('/players/{player_id}/trends')
def trends(player_id:int,metric:str='goals_per_90',season_id:int|None=Query(None,ge=1),
    window:int=Query(5,ge=1,le=20),min_samples:int|None=Query(None,ge=1,le=20),
    data_source:str|None=Query(None,min_length=1,max_length=255),db:Session=Depends(get_db)):
    return performance_trends(db,player_id,metric,season_id,window,min_samples,data_source)


@router.get('/scoring-models',response_model=list[ScoringModelResponse])
def scoring_models(db:Session=Depends(get_db)):
    return db.query(ScoringModel).order_by(ScoringModel.position_group,ScoringModel.created_at.desc()).limit(100).all()


@router.get('/scoring-models/{model_id}',response_model=ScoringModelResponse)
def scoring_model(model_id:int,db:Session=Depends(get_db)): return required(db,ScoringModel,model_id)


@router.post('/scoring-models',response_model=ScoringModelResponse,status_code=201)
def add_scoring_model(data:ScoringModelCreate,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    return create_model(db,data,user.id)


@router.get('/players/{player_id}/score')
def score(player_id:int,season_id:int|None=Query(None,ge=1),min_minutes:int=Query(450,ge=0,le=1000000),
    model_id:int|None=Query(None,ge=1),data_source:str|None=Query(None,min_length=1,max_length=255),
    min_peers:int=Query(3,ge=3,le=1000),db:Session=Depends(get_db)):
    return score_player(db,player_id,season_id,min_minutes,model_id,data_source,min_peers)
