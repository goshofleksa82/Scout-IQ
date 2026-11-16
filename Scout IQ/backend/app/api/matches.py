from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import Match, MatchEvent, MatchParticipant
from app.schemas.matches import MatchCreate, MatchResponse, MatchStatus, ParticipantCreate, ParticipantResponse, EventCreate, EventResponse
from app.services.entities import required
from app.services import matches as service
from app.repositories.pagination import paginate

router = APIRouter(prefix='/matches', tags=['Matches'])


@router.get('')
def matches(page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100), season_id: int | None = Query(None,ge=1), db: Session = Depends(get_db)):
    query = db.query(Match)
    if season_id is not None: query = query.filter(Match.season_id == season_id)
    result = paginate(query.order_by(Match.kickoff_at,Match.id),page,page_size)
    result['matches'] = [MatchResponse.model_validate(row) for row in result.pop('players')]
    return result


@router.post('', response_model=MatchResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_match(data: MatchCreate, db: Session = Depends(get_db)): return service.create_match(db,data)


@router.get('/{match_id}', response_model=MatchResponse)
def match(match_id: int, db: Session = Depends(get_db)): return required(db,Match,match_id)


@router.patch('/{match_id}', response_model=MatchResponse, dependencies=[Depends(require_admin)])
def update_match(match_id: int, data: MatchStatus, db: Session = Depends(get_db)):
    row = required(db,Match,match_id)
    if data.status=='scheduled' and db.query(MatchEvent).filter(MatchEvent.match_id==match_id).first() is not None:
        raise HTTPException(status_code=409,detail='A match with recorded events cannot be scheduled')
    row.status = data.status
    return service.commit(db,row)


@router.post('/{match_id}/participants', response_model=ParticipantResponse, status_code=201, dependencies=[Depends(require_admin)])
def participant(match_id: int, data: ParticipantCreate, db: Session = Depends(get_db)): return service.add_participant(db,match_id,data)


@router.get('/{match_id}/participants', response_model=list[ParticipantResponse])
def participants(match_id: int, db: Session = Depends(get_db)):
    required(db,Match,match_id)
    return db.query(MatchParticipant).filter(MatchParticipant.match_id == match_id).order_by(MatchParticipant.player_id).all()


@router.post('/{match_id}/events', response_model=EventResponse, status_code=201, dependencies=[Depends(require_admin)])
def event(match_id: int, data: EventCreate, db: Session = Depends(get_db)): return service.add_event(db,match_id,data)


@router.get('/{match_id}/events', response_model=list[EventResponse])
def events(match_id: int, db: Session = Depends(get_db)):
    required(db,Match,match_id)
    return db.query(MatchEvent).filter(MatchEvent.match_id == match_id).order_by(MatchEvent.minute,MatchEvent.added_time,MatchEvent.id).limit(500).all()


@router.get('/{match_id}/stats')
def statistics(match_id: int, db: Session = Depends(get_db)): return service.match_statistics(db,match_id)
