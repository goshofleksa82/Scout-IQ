from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


class ImportBatch(Base):
    __tablename__='import_batches'
    id: Mapped[int]=mapped_column(Identity(),primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='RESTRICT'),index=True)
    kind: Mapped[str]=mapped_column(String(20))
    source: Mapped[str]=mapped_column(String(255))
    rights_basis: Mapped[str]=mapped_column(String(255))
    status: Mapped[str]=mapped_column(String(20))
    report: Mapped[dict]=mapped_column(JSONB,default=dict,server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(CheckConstraint("status IN ('complete','rejected','failed')",name='ck_import_batch_status'),)


class ImportIdentity(Base):
    __tablename__='import_identities'
    id: Mapped[int]=mapped_column(Identity(),primary_key=True)
    source: Mapped[str]=mapped_column(String(255))
    kind: Mapped[str]=mapped_column(String(20))
    external_id: Mapped[str]=mapped_column(String(128))
    record_id: Mapped[int]=mapped_column(Integer)
    fingerprint: Mapped[str]=mapped_column(String(64))
    batch_id: Mapped[int]=mapped_column(ForeignKey('import_batches.id',ondelete='RESTRICT'),index=True)
    __table_args__=(UniqueConstraint('source','kind','external_id',name='uq_import_external_identity'),)
