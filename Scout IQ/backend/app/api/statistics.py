from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import Match, PlayerMatchStats
from app.schemas.statistics import StatsCreate, StatsResponse, StatsValues
from app.services.entities import required
from app.services.statistics import save_statistics, aggregate_statistics

router=APIRouter(tags=['Player match statistics'])


@router.post('/matches/{match_id}/player-stats',response_model=StatsResponse,status_code=201,dependencies=[Depends(require_admin)])
def create_stats(match_id:int,data:StatsCreate,db:Session=Depends(get_db)):
    return save_statistics(db,match_id,data.player_id,data)


@router.put('/matches/{match_id}/player-stats/{player_id}',response_model=StatsResponse,dependencies=[Depends(require_admin)])
def update_stats(match_id:int,player_id:int,data:StatsValues,db:Session=Depends(get_db)):
    return save_statistics(db,match_id,player_id,data,replace=True)


@router.get('/matches/{match_id}/player-stats',response_model=list[StatsResponse])
def match_stats(match_id:int,db:Session=Depends(get_db)):
    required(db,Match,match_id)
    return db.query(PlayerMatchStats).filter(PlayerMatchStats.match_id==match_id).order_by(PlayerMatchStats.player_id).all()


@router.get('/players/{player_id}/match-stats')
def totals(player_id:int,season_id:int|None=Query(None,ge=1),db:Session=Depends(get_db)):
    return aggregate_statistics(db,player_id,season_id)
