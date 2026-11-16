from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Identity, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


class PlayerMatchStats(Base):
    __tablename__ = 'player_match_stats'
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, index=True)
    player_id: Mapped[int] = mapped_column(Integer, index=True)
    minutes_played: Mapped[int] = mapped_column(Integer)
    goals: Mapped[int] = mapped_column(Integer)
    assists: Mapped[int] = mapped_column(Integer)
    shots: Mapped[int | None] = mapped_column(Integer)
    passes_attempted: Mapped[int | None] = mapped_column(Integer)
    passes_completed: Mapped[int | None] = mapped_column(Integer)
    tackles: Mapped[int | None] = mapped_column(Integer)
    progressive_passes: Mapped[int | None] = mapped_column(Integer)
    progressive_carries: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey('import_batches.id',ondelete='RESTRICT'))
    __table_args__ = (
        UniqueConstraint('player_id','match_id', name='uq_player_match_stats'),
        ForeignKeyConstraint(['match_id','player_id'],['match_participants.match_id','match_participants.player_id'],ondelete='CASCADE'),
        CheckConstraint('minutes_played BETWEEN 0 AND 180 AND goals >= 0 AND assists >= 0',name='ck_match_stats_nonnegative'),
        CheckConstraint('shots >= 0 AND passes_attempted >= 0 AND passes_completed >= 0 AND tackles >= 0 AND progressive_passes >= 0 AND progressive_carries >= 0',name='ck_match_stats_optional_nonnegative'),
        CheckConstraint('passes_completed <= passes_attempted AND goals <= shots',name='ck_match_stats_consistency'),
        CheckConstraint('minutes_played > 0 OR (goals=0 AND assists=0 AND coalesce(shots,0)=0 AND coalesce(passes_attempted,0)=0 AND coalesce(passes_completed,0)=0 AND coalesce(tackles,0)=0 AND coalesce(progressive_passes,0)=0 AND coalesce(progressive_carries,0)=0)',name='ck_match_stats_zero_minutes'),
    )
