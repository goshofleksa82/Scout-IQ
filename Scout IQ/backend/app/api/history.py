from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import Club, Membership, Player, Season
from app.repositories.pagination import paginate
from app.schemas import PlayerListResponse
from app.schemas.history import SeasonCreate, SeasonResponse, MembershipCreate, MembershipResponse, TransferRequest
from app.services.entities import required, save_entity
from app.services.history import add_membership

router = APIRouter(tags=['Seasons and transfers'])


@router.get('/seasons', response_model=list[SeasonResponse])
def seasons(db: Session = Depends(get_db)):
    return db.query(Season).order_by(Season.starts_on.desc(), Season.id).limit(100).all()


@router.post('/seasons', response_model=SeasonResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_season(data: SeasonCreate, db: Session = Depends(get_db)):
    return save_entity(db, Season, data)


@router.get('/players/{player_id}/memberships', response_model=list[MembershipResponse])
def memberships(player_id: int, db: Session = Depends(get_db)):
    required(db, Player, player_id)
    return db.query(Membership).filter(Membership.player_id == player_id).order_by(Membership.joined_on, Membership.id).all()


@router.post('/players/{player_id}/memberships', response_model=MembershipResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_membership(player_id: int, data: MembershipCreate, db: Session = Depends(get_db)):
    return add_membership(db, player_id, data)


@router.post('/players/{player_id}/transfers', response_model=MembershipResponse, status_code=201, dependencies=[Depends(require_admin)])
def transfer(player_id: int, data: TransferRequest, db: Session = Depends(get_db)):
    return add_membership(db, player_id, data, transfer=True)


@router.get('/players/history/search', response_model=PlayerListResponse)
def historical_players(club_id: int | None = Query(None, ge=1), on_date: date | None = None,
    season_id: int | None = Query(None, ge=1), page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Player).join(Membership)
    if club_id is not None:
        required(db, Club, club_id)
        query = query.filter(Membership.club_id == club_id)
    if on_date is not None:
        query = query.filter(Membership.joined_on <= on_date, or_(Membership.left_on.is_(None), Membership.left_on > on_date))
    if season_id is not None:
        season = required(db, Season, season_id)
        if on_date is not None and not season.starts_on <= on_date <= season.ends_on:
            raise HTTPException(status_code=400, detail='Search date is outside the season')
        query = query.filter(Membership.joined_on <= season.ends_on, or_(Membership.left_on.is_(None), Membership.left_on > season.starts_on))
    return paginate(query.distinct().order_by(Player.id), page, page_size)
