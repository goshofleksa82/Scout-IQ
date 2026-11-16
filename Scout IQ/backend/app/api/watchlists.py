from fastapi import APIRouter,Depends,Query,Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User,Player,Watchlist,WatchlistItem
from app.schemas import PlayerListResponse
from app.schemas.watchlists import WatchlistValues,WatchlistPlayer,WatchlistResponse
from app.services.entities import required
from app.services.watchlists import owned_watchlist,commit_watchlist
from app.repositories.pagination import paginate

router=APIRouter(prefix='/watchlists',tags=['Private watchlists'])


@router.get('')
def lists(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=db.query(Watchlist).filter(Watchlist.user_id==user.id)
    total=query.count();rows=query.order_by(Watchlist.updated_at.desc(),Watchlist.id).offset((page-1)*page_size).limit(page_size).all()
    counts=dict(db.query(WatchlistItem.watchlist_id,func.count()).filter(WatchlistItem.watchlist_id.in_([row.id for row in rows])).group_by(WatchlistItem.watchlist_id).all()) if rows else {}
    return {'watchlists':[{**WatchlistResponse.model_validate(row).model_dump(),'player_count':counts.get(row.id,0)} for row in rows],'total':total,'page':page,'page_size':page_size,'total_pages':(total+page_size-1)//page_size}


@router.post('',response_model=WatchlistResponse,status_code=201)
def create(data:WatchlistValues,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return commit_watchlist(db,Watchlist(user_id=user.id,**data.model_dump()))


@router.get('/{watchlist_id}',response_model=WatchlistResponse)
def detail(watchlist_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return owned_watchlist(db,user.id,watchlist_id)


@router.put('/{watchlist_id}',response_model=WatchlistResponse)
def edit(watchlist_id:int,data:WatchlistValues,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=owned_watchlist(db,user.id,watchlist_id,lock=True)
    for name,value in data.model_dump().items(): setattr(row,name,value)
    return commit_watchlist(db,row)


@router.delete('/{watchlist_id}',status_code=204)
def remove(watchlist_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=owned_watchlist(db,user.id,watchlist_id,lock=True);db.delete(row);commit_watchlist(db)
    return Response(status_code=204)


@router.get('/{watchlist_id}/players',response_model=PlayerListResponse)
def members(watchlist_id:int,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    owned_watchlist(db,user.id,watchlist_id)
    return paginate(db.query(Player).join(WatchlistItem,WatchlistItem.player_id==Player.id).filter(WatchlistItem.watchlist_id==watchlist_id).order_by(WatchlistItem.added_at.desc(),Player.id),page,page_size)


@router.post('/{watchlist_id}/players',status_code=201)
def add(watchlist_id:int,data:WatchlistPlayer,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=owned_watchlist(db,user.id,watchlist_id,lock=True);required(db,Player,data.player_id)
    db.add(WatchlistItem(watchlist_id=row.id,player_id=data.player_id));row.updated_at=func.now();commit_watchlist(db,row)
    return {'watchlist_id':row.id,'player_id':data.player_id}


@router.delete('/{watchlist_id}/players/{player_id}',status_code=204)
def remove_player(watchlist_id:int,player_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=owned_watchlist(db,user.id,watchlist_id,lock=True);item=db.get(WatchlistItem,(row.id,player_id))
    if item is not None: db.delete(item);row.updated_at=func.now();commit_watchlist(db,row)
    return Response(status_code=204)
