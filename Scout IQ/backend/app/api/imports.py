from typing import Literal
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import ImportBatch, User
from app.services.entities import required
from app.services.imports import import_csv

router=APIRouter(prefix='/imports',tags=['Data imports'])


@router.post('/{kind}',openapi_extra={'requestBody':{'required':True,'content':{'text/csv':{'schema':{'type':'string'}}}}})
async def upload_csv(kind:Literal['players','matches','player-stats'],request:Request,
    source:str=Query(min_length=1,max_length=255),rights_basis:str=Query(min_length=1,max_length=255),
    rights_confirmed:bool=Query(False),user:User=Depends(require_admin),db:Session=Depends(get_db)):
    if not rights_confirmed: raise HTTPException(status_code=400,detail='Confirm permission to store and process this dataset')
    chunks=[]; size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>2*1024*1024: raise HTTPException(status_code=413,detail='CSV exceeds the 2 MiB limit')
        chunks.append(chunk)
    report,status=import_csv(db,user.id,kind,source,rights_basis,b''.join(chunks))
    return JSONResponse(status_code=status,content=report)


@router.get('/batches/{batch_id}',dependencies=[Depends(require_admin)])
def batch_report(batch_id:int,db:Session=Depends(get_db)):
    batch=required(db,ImportBatch,batch_id)
    return {'batch_id':batch.id,'source':batch.source,'rights_basis':batch.rights_basis,'kind':batch.kind,'status':batch.status,'created_at':batch.created_at,**batch.report}
