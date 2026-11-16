from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Club, Competition, Player


def required(db, model, entity_id):
    row = db.get(model, entity_id)
    if row is None: raise HTTPException(status_code=404, detail=model.__name__ + " not found")
    return row


def save_entity(db, model, data, entity_id=None):
    values = data.model_dump()
    if model is Club and values.get('competition_id') is not None:
        required(db, Competition, values['competition_id'])
    row = model(**values) if entity_id is None else required(db, model, entity_id)
    try:
        for key, value in values.items(): setattr(row, key, value)
        db.add(row)
        db.flush()
        if model is Club and entity_id is not None:
            db.execute(update(Player).where(Player.club_id == row.id).values(club=row.name))
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate entity or invalid relationship") from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to save entity") from None


def delete_entity(db, model, entity_id):
    row = required(db, model, entity_id)
    try:
        db.delete(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Entity is referenced by other records") from None
