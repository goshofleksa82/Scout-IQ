from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,Query,Response
from sqlalchemy import func,select,delete
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user,require_admin
from app.models import User,ProductEvent,BetaFeedback
from app.schemas.product import PreferencesUpdate,FeatureEvent,FeedbackCreate,FeedbackReview
from app.services.entities import required

router=APIRouter(tags=['Beta product workflow'])


def preferences(user):
    return {'analytics_opt_in':user.analytics_opt_in,'onboarding_completed_at':user.onboarding_completed_at,'event_retention_days':90,'note':'Optional feature events contain only an account identifier, an approved event name and time. Search terms, player selections, observations, IP addresses and device identifiers are not stored in product events.'}


@router.get('/product/preferences')
def get_preferences(user:User=Depends(get_current_user)): return preferences(user)


@router.patch('/product/preferences')
def update_preferences(data:PreferencesUpdate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    user.analytics_opt_in=data.analytics_opt_in
    if data.onboarding_completed is True and user.onboarding_completed_at is None: user.onboarding_completed_at=datetime.now(timezone.utc)
    if not data.analytics_opt_in: db.execute(delete(ProductEvent).where(ProductEvent.user_id==user.id))
    db.commit();db.refresh(user);return preferences(user)


@router.post('/product/events',status_code=204)
def record_event(data:FeatureEvent,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    # Serialize against consent withdrawal: a concurrent opt-out removes previous
    # events and cannot be followed by an event using stale consent.
    user=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if user.analytics_opt_in:
        # Retain at most one observation of a feature per account per minute.
        cutoff=datetime.now(timezone.utc)-timedelta(minutes=1)
        exists=db.scalar(select(ProductEvent.id).where(ProductEvent.user_id==user.id,ProductEvent.event==data.event,ProductEvent.created_at>=cutoff).limit(1))
        if exists is None: db.add(ProductEvent(user_id=user.id,event=data.event));db.commit()
    return Response(status_code=204)


def feedback_payload(row,admin=False):
    result={key:getattr(row,key) for key in ('id','author_id','category','area','rating','message','follow_up','status','priority','created_at','updated_at')}
    if admin: result['admin_note']=row.admin_note
    return result


@router.post('/feedback',status_code=201)
def submit_feedback(data:FeedbackCreate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=BetaFeedback(author_id=user.id,**data.model_dump());db.add(row);db.commit();db.refresh(row);return feedback_payload(row)


@router.get('/feedback')
def own_feedback(page:int=Query(1,ge=1),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=db.query(BetaFeedback).filter(BetaFeedback.author_id==user.id);total=query.count()
    return {'feedback':[feedback_payload(r) for r in query.order_by(BetaFeedback.id.desc()).offset((page-1)*20).limit(20)],'total':total,'page':page,'total_pages':(total+19)//20}


@router.get('/admin/feedback')
def beta_feedback(status:str|None=Query(None,max_length=20),page:int=Query(1,ge=1),user:User=Depends(require_admin),db:Session=Depends(get_db)):
    query=db.query(BetaFeedback)
    if status: query=query.filter(BetaFeedback.status==status)
    total=query.count()
    return {'feedback':[feedback_payload(r,True) for r in query.order_by(BetaFeedback.id.desc()).offset((page-1)*20).limit(20)],'total':total,'page':page,'total_pages':(total+19)//20}


@router.patch('/admin/feedback/{feedback_id}')
def review_feedback(feedback_id:int,data:FeedbackReview,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    row=required(db,BetaFeedback,feedback_id)
    for key,value in data.model_dump().items(): setattr(row,key,value)
    db.commit();db.refresh(row);return feedback_payload(row,True)


@router.get('/admin/product-metrics')
def product_metrics(user:User=Depends(require_admin),db:Session=Depends(get_db)):
    cutoff=datetime.now(timezone.utc)-timedelta(days=30)
    counts=db.query(ProductEvent.event,func.count(),func.count(func.distinct(ProductEvent.user_id))).filter(ProductEvent.created_at>=cutoff).group_by(ProductEvent.event).order_by(ProductEvent.event).all()
    feedback=db.query(BetaFeedback.status,func.count()).group_by(BetaFeedback.status).all()
    return {'period_days':30,'analytics_opted_in':db.query(User).filter(User.analytics_opt_in.is_(True)).count(),'onboarding_completed':db.query(User).filter(User.onboarding_completed_at.is_not(None)).count(),'events':[{'event':r[0],'count':r[1],'accounts':r[2]} for r in counts],'feedback_statuses':dict(feedback),'note':'Feature usage covers consenting accounts only; events are deduplicated per account, feature and minute. Feedback counts are submitted feedback, not recruited testers or a representative customer sample.'}
