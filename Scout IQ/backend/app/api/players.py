"""ScoutIQ API: database-backed endpoints with Pydantic response validation."""
from fastapi import Depends, APIRouter, HTTPException, Query, status
from app.repositories.pagination import paginate
from typing import Annotated
from app.repositories.players import search_players as query_players
from app.services.player_metrics import per90, comparison_stats
from app.services import player_writes as writes
from app.repositories.players import ordered_players, player_by_id
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.dependencies import require_admin

import logging

from app.core.database import get_db
from app.models import Player

from app.schemas import (
    PlayerComparisonResponse,
    PlayerListResponse,
    PlayerRankingEntry,
    PlayerRankingsResponse,
    PlayerResponse,
    PlayerStatsResponse,
    PlayerCreate,
    PlayerUpdate, PlayerSearch
)

router = APIRouter(tags=["Players"])

logger = logging.getLogger(__name__)


@router.get('/')
def home():
    return {'message': 'Welcome to ScoutIQ'}


@router.get('/players', response_model=PlayerListResponse)
def get_players(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return paginate(ordered_players(db), page, page_size)


@router.get('/players/count')
def count_players(db: Session = Depends(get_db)):
    return {'count': db.query(Player).count()}


@router.get('/players/search', response_model=PlayerListResponse)
def search_players(filters: Annotated[PlayerSearch, Query()], db: Session = Depends(get_db)):
    return query_players(db, filters)


@router.get('/players/filter', response_model=list[PlayerResponse])
def filter_players(
    position: str | None = None,
    club: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    db: Session = Depends(get_db),
):
    if min_age is not None and min_age < 0:
        raise HTTPException(status_code=400, detail='Minimum age cannot be negative')
    if max_age is not None and max_age < 0:
        raise HTTPException(status_code=400, detail='Maximum age cannot be negative')
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=400, detail='Minimum age cannot be greater than maximum age')
    query = db.query(Player)
    if position is not None:
        query = query.filter(func.lower(Player.position) == position.lower())
    if club is not None:
        query = query.filter(func.lower(Player.club) == club.lower())
    if min_age is not None:
        query = query.filter(Player.age >= min_age)
    if max_age is not None:
        query = query.filter(Player.age <= max_age)
    return query.order_by(Player.id).all()


@router.get('/players/sort', response_model=list[PlayerResponse])
def sort_players(sort_by: str = 'goals', order: str = 'desc', db: Session = Depends(get_db)):
    allowed = {'goals': Player.goals, 'assists': Player.assists, 'age': Player.age}
    if sort_by not in allowed:
        raise HTTPException(status_code=400, detail='Invalid sorting field')
    if order not in {'asc', 'desc'}:
        raise HTTPException(status_code=400, detail='Invalid sorting order')
    column = allowed[sort_by]
    criterion = column.asc() if order == 'asc' else column.desc()
    return db.query(Player).order_by(criterion, Player.id).all()






@router.get('/players/compare', response_model=PlayerComparisonResponse)
def compare_players(player1: int, player2: int, db: Session = Depends(get_db)):
    if player1 == player2:
        raise HTTPException(status_code=400, detail='Cannot compare a player with themselves')
    first = db.get(Player, player1)
    second = db.get(Player, player2)
    if first is None or second is None:
        raise HTTPException(status_code=404, detail='Player not found')
    return {'player1': comparison_stats(first), 'player2': comparison_stats(second)}


@router.get('/players/rankings', response_model=PlayerRankingsResponse)
def rank_players(
    metric: str = 'goals_per_90',
    position: str | None = None,
    min_minutes: int = 0,
    db: Session = Depends(get_db),
):
    allowed = {'goals_per_90', 'assists_per_90', 'goal_contributions_per_90'}
    if metric not in allowed:
        raise HTTPException(status_code=400, detail='Invalid ranking metric')
    if min_minutes < 0:
        raise HTTPException(status_code=400, detail='Minimum minutes cannot be negative')
    query = db.query(Player).filter(Player.minutes_played > 0, Player.minutes_played >= min_minutes)
    if position is not None:
        query = query.filter(func.lower(Player.position) == position.lower())
    players = query.all()
    players.sort(key=lambda p: (-per90(p, metric), p.id))
    entries = [
        PlayerRankingEntry(rank=index, player_id=p.id, name=p.name, position=p.position, value=per90(p, metric))
        for index, p in enumerate(players, start=1)
    ]
    return {'metric': metric, 'rankings': entries}


@router.get('/players/{player_id}/stats', response_model=PlayerStatsResponse)
def player_stats(player_id: int, db: Session = Depends(get_db)):
    player = player_by_id(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail='Player not found')
    if player.minutes_played <= 0:
        raise HTTPException(status_code=400, detail='Player has no minutes played')
    return {
        'player_id': player.id,
        'name': player.name,
        'goals_per_90': per90(player, 'goals_per_90'),
        'assists_per_90': per90(player, 'assists_per_90'),
        'goal_contributions_per_90': per90(player, 'goal_contributions_per_90'),
    }


@router.get('/players/{player_id}', response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = player_by_id(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail='Player not found')
    return player

@router.post(
    "/players",
    response_model=PlayerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_player(
    player: PlayerCreate,
    db: Session = Depends(get_db)
):
    return writes.create_player(db, player)


@router.patch(
    "/players/{player_id}",
    response_model=PlayerResponse,
    dependencies=[Depends(require_admin)],
)
def update_player(
    player_id: int,
    updates: PlayerUpdate,
    db: Session = Depends(get_db)
):
    return writes.update_player(db, player_id, updates)




@router.delete(
    "/players/{player_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_player(
    player_id: int,
    db: Session = Depends(get_db)
):
    return writes.delete_player(db, player_id)


