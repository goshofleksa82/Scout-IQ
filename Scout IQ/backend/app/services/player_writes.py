"""Player write operations with transaction rollback and stable API errors."""
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging
from app.models import Player, Membership
logger = logging.getLogger(__name__)

def create_player(db, player):
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


def update_player(db, player_id, updates):
    try:
        player = db.get(Player, player_id)

        if player is None:
            raise HTTPException(
                status_code=404,
                detail="Player not found"
            )

        update_data = updates.model_dump(exclude_unset=True)
        if any(key in update_data for key in ('club', 'club_id')) and db.query(Membership).filter(Membership.player_id == player_id).first():
            raise HTTPException(status_code=409, detail='Use the transfer endpoint to change a player with recorded memberships')

        for field, value in update_data.items():
            setattr(player, field, value)

        if update_data:
            db.commit()
            db.refresh(player)

        return player

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error while updating player")

        raise HTTPException(
            status_code=409,
            detail="Player update violates a database constraint"
        ) from None

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error while updating player")

        raise HTTPException(
            status_code=500,
            detail="Unable to update player"
        ) from None


def delete_player(db, player_id):
    try:
        player = db.get(Player, player_id)

        if player is None:
            raise HTTPException(
                status_code=404,
                detail="Player not found"
            )

        db.delete(player)
        db.commit()

        return None

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error while deleting player")

        raise HTTPException(
            status_code=409,
            detail="Player cannot be deleted due to a database constraint"
        ) from None

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error while deleting player")

        raise HTTPException(
            status_code=500,
            detail="Unable to delete player"
        ) from None


