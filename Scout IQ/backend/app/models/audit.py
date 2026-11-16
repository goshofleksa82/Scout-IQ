from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,Identity,Integer,String,CheckConstraint,func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.models import Base


class AuditLog(Base):
    __tablename__='audit_logs'
    id:Mapped[int]=mapped_column(Identity(),primary_key=True)
    actor_id:Mapped[int|None]=mapped_column(Integer,index=True)
    entity:Mapped[str]=mapped_column(String(80),index=True)
    action:Mapped[str]=mapped_column(String(10))
    record_key:Mapped[dict]=mapped_column(JSONB)
    before:Mapped[dict|None]=mapped_column(JSONB,nullable=True)
    after:Mapped[dict|None]=mapped_column(JSONB,nullable=True)
    changed_fields:Mapped[list]=mapped_column(JSONB)
    source:Mapped[str]=mapped_column(String(30))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
    __table_args__=(CheckConstraint("action IN ('create','update','delete')",name='ck_audit_action'),)


class DataQualityRun(Base):
    __tablename__='data_quality_runs'
    id:Mapped[int]=mapped_column(Identity(),primary_key=True)
    created_by_id:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    summary:Mapped[dict]=mapped_column(JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
