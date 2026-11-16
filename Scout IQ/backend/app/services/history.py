from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Club, Membership, Player, Season
from app.services.entities import required


def add_membership(db, player_id, data, transfer=False):
    player = db.scalar(select(Player).where(Player.id == player_id).with_for_update().execution_options(populate_existing=True))
    if player is None: raise HTTPException(status_code=404, detail='Player not found')
    club = required(db, Club, data.club_id)
    season = required(db, Season, data.season_id)
    joined = data.transfer_date if transfer else data.joined_on
    if not season.starts_on <= joined <= season.ends_on:
        raise HTTPException(status_code=400, detail='Joining date must be within its season')
    row = Membership(player_id=player_id, club_id=club.id, season_id=season.id,
                     joined_on=joined, left_on=None if transfer else data.left_on)
    try:
        if transfer:
            latest = db.scalar(select(Membership).where(Membership.player_id == player_id).order_by(Membership.joined_on.desc()).limit(1))
            if latest is not None and joined <= latest.joined_on:
                raise HTTPException(status_code=400, detail='Transfer must follow the latest recorded membership')
            if club.id == player.club_id:
                raise HTTPException(status_code=400, detail='Player already belongs to this club')
            opened = db.scalar(select(Membership).where(Membership.player_id == player_id, Membership.left_on.is_(None)))
            if opened is not None: opened.left_on = joined
            row.previous_club_id = player.club_id
            player.current_club = club
            player.club = club.name
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Membership overlaps an existing record or references invalid data') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail='Unable to save membership') from None
