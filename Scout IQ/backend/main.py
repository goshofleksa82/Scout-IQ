"""ScoutIQ API: database-backed endpoints with Pydantic response validation."""
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import logging

from database import get_db
from models import Player

from schemas import (
    PlayerComparisonResponse,
    PlayerListResponse,
    PlayerRankingEntry,
    PlayerRankingsResponse,
    PlayerResponse,
    PlayerStatsResponse,
    PlayerCreate
)

app = FastAPI(title='ScoutIQ', version='1.0.0')

logger = logging.getLogger(__name__)


@app.get('/')
def home():
    return {'message': 'Welcome to ScoutIQ'}


@app.get('/players', response_model=PlayerListResponse)
def get_players(db: Session = Depends(get_db)):
    return {'players': db.query(Player).order_by(Player.id).all()}


@app.get('/players/count')
def count_players(db: Session = Depends(get_db)):
    return {'count': db.query(Player).count()}


@app.get('/players/filter', response_model=list[PlayerResponse])
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


@app.get('/players/sort', response_model=list[PlayerResponse])
def sort_players(sort_by: str = 'goals', order: str = 'desc', db: Session = Depends(get_db)):
    allowed = {'goals': Player.goals, 'assists': Player.assists, 'age': Player.age}
    if sort_by not in allowed:
        raise HTTPException(status_code=400, detail='Invalid sorting field')
    if order not in {'asc', 'desc'}:
        raise HTTPException(status_code=400, detail='Invalid sorting order')
    column = allowed[sort_by]
    criterion = column.asc() if order == 'asc' else column.desc()
    return db.query(Player).order_by(criterion, Player.id).all()


def per90(player: Player, metric: str) -> float:
    if metric == 'goals_per_90':
        count = player.goals
    elif metric == 'assists_per_90':
        count = player.assists
    else:
        count = player.goals + player.assists
    return round(count * 90 / player.minutes_played, 2)


def comparison_stats(player: Player) -> dict:
    data = {
        'name': player.name,
        'club': player.club,
        'position': player.position,
        'goals': player.goals,
        'assists': player.assists,
        'minutes_played': player.minutes_played,
        'goals_per_90': None,
        'assists_per_90': None,
        'goal_contributions_per_90': None,
    }
    if player.minutes_played > 0:
        for metric in ('goals_per_90', 'assists_per_90', 'goal_contributions_per_90'):
            data[metric] = per90(player, metric)
    return data


@app.get('/players/compare', response_model=PlayerComparisonResponse)
def compare_players(player1: int, player2: int, db: Session = Depends(get_db)):
    if player1 == player2:
        raise HTTPException(status_code=400, detail='Cannot compare a player with themselves')
    first = db.get(Player, player1)
    second = db.get(Player, player2)
    if first is None or second is None:
        raise HTTPException(status_code=404, detail='Player not found')
    return {'player1': comparison_stats(first), 'player2': comparison_stats(second)}


@app.get('/players/rankings', response_model=PlayerRankingsResponse)
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


@app.get('/players/{player_id}/stats', response_model=PlayerStatsResponse)
def player_stats(player_id: int, db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
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


@app.get('/players/{player_id}', response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail='Player not found')
    return player

@app.post(
    "/players",
    response_model=PlayerResponse,
    status_code=status.HTTP_201_CREATED
)
def create_player(
    player: PlayerCreate,
    db: Session = Depends(get_db)
):
    new_player = Player(**player.model_dump())

    try:
        db.add(new_player)
        db.commit()
        db.refresh(new_player)

    except IntegrityError:
        db.rollback()

        logger.exception(
            "Database integrity violation while creating player"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Player could not be created due to a database constraint"
        ) from None

    except SQLAlchemyError:
        db.rollback()

        logger.exception(
            "Database error while creating player"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create player"
        ) from None

    return new_player

