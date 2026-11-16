from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import AuditLog,DataQualityRun,User
from app.services.data_quality import run_checks
from app.services.watchlists import commit_watchlist

router=APIRouter(prefix='/admin',tags=['Data quality and audit'],dependencies=[Depends(require_admin)])


@router.get('/audit')
def audit(entity:str|None=Query(None,max_length=80),actor_id:int|None=Query(None,ge=1),record_id:int|None=Query(None,ge=1),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    query=db.query(AuditLog)
    if entity: query=query.filter(AuditLog.entity==entity)
    if actor_id is not None: query=query.filter(AuditLog.actor_id==actor_id)
    if record_id is not None: query=query.filter(AuditLog.record_key['id'].astext==str(record_id))
    total=query.count();rows=query.order_by(AuditLog.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'events':[{'id':r.id,'actor_id':r.actor_id,'entity':r.entity,'action':r.action,'record_key':r.record_key,'before':r.before,'after':r.after,'changed_fields':r.changed_fields,'source':r.source,'created_at':r.created_at} for r in rows],'total':total,'page':page,'page_size':page_size,'total_pages':(total+page_size-1)//page_size,'note':'Capture begins when audit triggers are installed. Legacy changes are not reconstructed. Sensitive and private content is excluded; attribution can be unavailable for direct system writes.'}


@router.get('/data-quality')
def preview(db:Session=Depends(get_db)): return run_checks(db)


@router.post('/data-quality/runs',status_code=201)
def run(user:User=Depends(require_admin),db:Session=Depends(get_db)):
    result=run_checks(db);row=DataQualityRun(created_by_id=user.id,summary=result)
    db.add(row);db.commit();db.refresh(row)
    return {'id':row.id,'created_at':row.created_at,**row.summary}


@router.get('/data-quality/runs')
def runs(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    query=db.query(DataQualityRun);total=query.count();rows=query.order_by(DataQualityRun.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'runs':[{'id':r.id,'created_by_id':r.created_by_id,'created_at':r.created_at,'summary':r.summary} for r in rows],'total':total,'page':page,'total_pages':(total+page_size-1)//page_size}
