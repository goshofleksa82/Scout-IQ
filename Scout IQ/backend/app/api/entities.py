from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import Club, Competition, Player
from app.schemas import PlayerListResponse
from app.schemas.entities import EntityCreate, ClubCreate, ClubResponse, CompetitionResponse
from app.services.entities import required, save_entity, delete_entity
from app.repositories.pagination import paginate

router = APIRouter(tags=['Football entities'])


@router.get('/clubs', response_model=list[ClubResponse])
def clubs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return db.query(Club).order_by(Club.id).offset((page-1)*page_size).limit(page_size).all()


@router.get('/clubs/{club_id}', response_model=ClubResponse)
def club(club_id: int, db: Session = Depends(get_db)):
    return required(db, Club, club_id)


@router.post('/clubs', response_model=ClubResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_club(data: ClubCreate, db: Session = Depends(get_db)):
    return save_entity(db, Club, data)


@router.put('/clubs/{club_id}', response_model=ClubResponse, dependencies=[Depends(require_admin)])
def update_club(club_id: int, data: ClubCreate, db: Session = Depends(get_db)):
    return save_entity(db, Club, data, club_id)


@router.delete('/clubs/{club_id}', status_code=204, dependencies=[Depends(require_admin)])
def remove_club(club_id: int, db: Session = Depends(get_db)):
    delete_entity(db, Club, club_id)


@router.get('/clubs/{club_id}/players', response_model=PlayerListResponse)
def club_players(club_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    required(db, Club, club_id)
    return paginate(db.query(Player).filter(Player.club_id == club_id).order_by(Player.id), page, page_size)


@router.get('/competitions', response_model=list[CompetitionResponse])
def competitions(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return db.query(Competition).order_by(Competition.id).offset((page-1)*page_size).limit(page_size).all()


@router.get('/competitions/{competition_id}', response_model=CompetitionResponse)
def competition(competition_id: int, db: Session = Depends(get_db)):
    return required(db, Competition, competition_id)


@router.post('/competitions', response_model=CompetitionResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_competition(data: EntityCreate, db: Session = Depends(get_db)):
    return save_entity(db, Competition, data)


@router.put('/competitions/{competition_id}', response_model=CompetitionResponse, dependencies=[Depends(require_admin)])
def update_competition(competition_id: int, data: EntityCreate, db: Session = Depends(get_db)):
    return save_entity(db, Competition, data, competition_id)


@router.delete('/competitions/{competition_id}', status_code=204, dependencies=[Depends(require_admin)])
def remove_competition(competition_id: int, db: Session = Depends(get_db)):
    delete_entity(db, Competition, competition_id)


@router.get('/competitions/{competition_id}/clubs', response_model=list[ClubResponse])
def competition_clubs(competition_id: int, db: Session = Depends(get_db)):
    required(db, Competition, competition_id)
    return db.query(Club).filter(Club.competition_id == competition_id).order_by(Club.id).limit(100).all()
