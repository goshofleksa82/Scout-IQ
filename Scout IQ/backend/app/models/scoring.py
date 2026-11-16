from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


class ScoringModel(Base):
    __tablename__='scoring_models'
    id: Mapped[int]=mapped_column(Identity(),primary_key=True)
    name: Mapped[str]=mapped_column(String(100))
    version: Mapped[str]=mapped_column(String(20))
    position_group: Mapped[str]=mapped_column(String(20))
    weights: Mapped[dict]=mapped_column(JSONB)
    description: Mapped[str]=mapped_column(String(1000))
    created_by_id: Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(
        UniqueConstraint('position_group','version',name='uq_scoring_model_group_version'),
        CheckConstraint("position_group IN ('strikers','wingers','midfielders','defenders','goalkeepers')",name='ck_scoring_group'),
        CheckConstraint("version ~ '^(0|[1-9][0-9]{0,3})[.](0|[1-9][0-9]{0,3})[.](0|[1-9][0-9]{0,3})$'",name='ck_scoring_version'),
    )
