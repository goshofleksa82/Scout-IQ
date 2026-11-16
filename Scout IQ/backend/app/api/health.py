from fastapi import APIRouter,Depends,Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.operations import snapshot

router=APIRouter(tags=['Operations'])


@router.get('/health/live')
def live(): return {'status':'ok'}


@router.get('/health/ready')
def ready(response:Response,db:Session=Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
        # Readiness also requires the deployed schema revision, not merely a socket.
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from pathlib import Path
        config=Config(str(Path(__file__).resolve().parents[2]/'alembic.ini'))
        config.set_main_option('script_location',str(Path(__file__).resolve().parents[2]/'migrations'))
        expected=ScriptDirectory.from_config(config).get_current_head()
        current=db.scalar(text('SELECT version_num FROM alembic_version'))
        if current!=expected: response.status_code=503;return {'status':'not_ready'}
        return {'status':'ready'}
    except SQLAlchemyError:
        db.rollback();response.status_code=503;return {'status':'not_ready'}


@router.get('/admin/operations',dependencies=[Depends(require_admin)])
def operations(): return snapshot()
