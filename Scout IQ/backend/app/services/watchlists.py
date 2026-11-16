from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from app.models import Watchlist


def owned_watchlist(db,user_id,watchlist_id,lock=False):
    query=select(Watchlist).where(Watchlist.id==watchlist_id,Watchlist.user_id==user_id)
    if lock: query=query.with_for_update()
    row=db.scalar(query)
    if row is None: raise HTTPException(status_code=404,detail='Watchlist not found')
    return row


def commit_watchlist(db,row=None):
    try:
        if row is not None: db.add(row)
        db.commit()
        if row is not None: db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail='A watchlist or player entry already exists, or a relationship changed') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500,detail='Unable to save watchlist') from None
