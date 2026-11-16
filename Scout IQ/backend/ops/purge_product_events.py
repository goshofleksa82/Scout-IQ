"""Run daily via the chosen host's job runner. Does not delete scouting data."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import delete
from app.core.database import SessionLocal
from app.models import ProductEvent
with SessionLocal() as db:
    result=db.execute(delete(ProductEvent).where(ProductEvent.created_at<datetime.now(timezone.utc)-timedelta(days=90)))
    db.commit();print('Expired feature events removed:',result.rowcount)
