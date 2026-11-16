from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User,ScoutingReport,ScoutingReportVersion
from app.schemas.reports import ReportCreate,ReportEdit,ReportResponse
from app.services.reports import owned_report,save_report

router=APIRouter(prefix='/reports',tags=['Private scouting reports'])


@router.get('')
def reports(player_id:int|None=Query(None,ge=1),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=db.query(ScoutingReport).filter(ScoutingReport.author_id==user.id)
    if player_id is not None: query=query.filter(ScoutingReport.player_id==player_id)
    total=query.count();rows=query.order_by(ScoutingReport.updated_at.desc(),ScoutingReport.id).offset((page-1)*page_size).limit(page_size).all()
    return {'reports':[ReportResponse.model_validate(row) for row in rows],'total':total,'page':page,'page_size':page_size,'total_pages':(total+page_size-1)//page_size}


@router.post('',response_model=ReportResponse,status_code=201)
def create(data:ReportCreate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return save_report(db,user.id,data)


@router.get('/{report_id}',response_model=ReportResponse)
def detail(report_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return owned_report(db,user.id,report_id)


@router.put('/{report_id}',response_model=ReportResponse)
def edit(report_id:int,data:ReportEdit,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return save_report(db,user.id,data,report_id)


@router.get('/{report_id}/history')
def history(report_id:int,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    owned_report(db,user.id,report_id)
    query=db.query(ScoutingReportVersion).filter(ScoutingReportVersion.report_id==report_id)
    total=query.count();rows=query.order_by(ScoutingReportVersion.version.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'revisions':[{'version':row.version,'created_at':row.created_at,'content':row.content} for row in rows],'total':total,'page':page,'page_size':page_size,'total_pages':(total+page_size-1)//page_size}
