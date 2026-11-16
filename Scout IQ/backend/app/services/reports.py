from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.models import ScoutingReport,ScoutingReportVersion,Player
from app.schemas.reports import ReportValues,ReportResponse
from app.services.entities import required


def owned_report(db,user_id,report_id,lock=False):
    query=select(ScoutingReport).where(ScoutingReport.id==report_id,ScoutingReport.author_id==user_id)
    if lock: query=query.with_for_update()
    row=db.scalar(query)
    if row is None: raise HTTPException(status_code=404,detail='Scouting report not found')
    return row


def save_report(db,user_id,data,report_id=None):
    row=owned_report(db,user_id,report_id,lock=True) if report_id is not None else None
    if row is not None and row.version!=data.expected_version: raise HTTPException(status_code=409,detail='This report has a newer revision. Reload it before editing.')
    if row is None: required(db,Player,data.player_id)
    values=data.model_dump(exclude={'player_id','expected_version'})
    row=row or ScoutingReport(author_id=user_id,player_id=data.player_id,version=0)
    for name,value in values.items(): setattr(row,name,value)
    row.version+=1
    try:
        db.add(row);db.flush()
        db.add(ScoutingReportVersion(report_id=row.id,version=row.version,content=ReportValues.model_validate(values).model_dump(mode='json')))
        # Materialize before commit so response reads cannot race a later edit.
        payload=ReportResponse.model_validate(row)
        db.commit();return payload
    except SQLAlchemyError:
        db.rollback();raise HTTPException(status_code=500,detail='Unable to save scouting report') from None
