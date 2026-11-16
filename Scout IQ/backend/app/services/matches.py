from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Club, Competition, Match, MatchEvent, MatchParticipant, Membership, Player, PlayerMatchStats, Season
from app.services.entities import required


def commit(db, row):
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Duplicate record or invalid match relationship') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail='Unable to save match data') from None


def create_match(db, data):
    required(db, Club, data.home_club_id)
    required(db, Club, data.away_club_id)
    required(db, Competition, data.competition_id)
    season = required(db, Season, data.season_id)
    if not season.starts_on <= data.kickoff_at.astimezone(timezone.utc).date() <= season.ends_on:
        raise HTTPException(status_code=400, detail='Match date must be within its season')
    return commit(db, Match(**data.model_dump()))


def add_participant(db, match_id, data):
    match = required(db, Match, match_id)
    required(db, Player, data.player_id)
    if data.club_id not in {match.home_club_id, match.away_club_id}:
        raise HTTPException(status_code=400, detail='Participant club must play in the match')
    day = match.kickoff_at.astimezone(timezone.utc).date()
    membership = db.scalar(select(Membership).where(Membership.player_id == data.player_id,
        Membership.club_id == data.club_id, Membership.joined_on <= day,
        or_(Membership.left_on.is_(None), Membership.left_on > day)))
    if membership is None:
        raise HTTPException(status_code=400, detail='A dated club membership is required for participation')
    return commit(db, MatchParticipant(match_id=match_id, **data.model_dump()))


def add_event(db, match_id, data):
    match = required(db, Match, match_id)
    participant = db.get(MatchParticipant, (match_id, data.player_id))
    if participant is None: raise HTTPException(status_code=400, detail='Player is not a registered participant')
    if match.status == 'scheduled': raise HTTPException(status_code=400, detail='Scheduled matches cannot have recorded events')
    if data.minute > match.duration_minutes: raise HTTPException(status_code=400, detail='Event minute exceeds match duration')
    if data.event_type in {'goal','assist'}:
        stats = db.scalar(select(PlayerMatchStats).where(PlayerMatchStats.match_id==match_id,PlayerMatchStats.player_id==data.player_id))
        if stats is not None:
            count = db.scalar(select(func.count()).select_from(MatchEvent).where(MatchEvent.match_id==match_id,MatchEvent.player_id==data.player_id,MatchEvent.event_type==data.event_type))
            if getattr(stats,'goals' if data.event_type=='goal' else 'assists') < count+1:
                raise HTTPException(status_code=400,detail='Update recorded player statistics before adding this event')
    if data.related_goal_id is not None:
        goal = required(db, MatchEvent, data.related_goal_id)
        if (goal.match_id != match_id or goal.event_type != 'goal' or goal.club_id != participant.club_id
            or goal.player_id == data.player_id or (goal.minute, goal.added_time) != (data.minute, data.added_time)):
            raise HTTPException(status_code=400, detail='Assist must reference a teammate goal at the same timestamp')
    return commit(db, MatchEvent(match_id=match_id, **data.model_dump()))


def match_statistics(db, match_id):
    match = required(db, Match, match_id)
    rows = db.execute(select(MatchParticipant.club_id, MatchEvent.event_type, func.count(MatchEvent.id))
        .join(MatchEvent, (MatchParticipant.match_id == MatchEvent.match_id) & (MatchParticipant.player_id == MatchEvent.player_id))
        .where(MatchEvent.match_id == match_id).group_by(MatchParticipant.club_id, MatchEvent.event_type)).all()
    counts = {(club, event): count for club, event, count in rows}
    def team(club): return {name: counts.get((club, name), 0) for name in ('goal','assist','yellow_card','red_card')}
    return {'match_id':match.id, 'home':team(match.home_club_id), 'away':team(match.away_club_id)}
