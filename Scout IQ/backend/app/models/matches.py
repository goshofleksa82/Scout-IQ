from __future__ import annotations
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base


class Match(Base):
    __tablename__ = 'matches'
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    home_club_id: Mapped[int] = mapped_column(ForeignKey('clubs.id', ondelete='RESTRICT'))
    away_club_id: Mapped[int] = mapped_column(ForeignKey('clubs.id', ondelete='RESTRICT'))
    competition_id: Mapped[int] = mapped_column(ForeignKey('competitions.id', ondelete='RESTRICT'), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey('seasons.id', ondelete='RESTRICT'), index=True)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=90, server_default='90')
    status: Mapped[str] = mapped_column(String(20), default='scheduled', server_default='scheduled')
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey('import_batches.id',ondelete='RESTRICT'))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        CheckConstraint('home_club_id <> away_club_id', name='ck_match_distinct_clubs'),
        CheckConstraint('duration_minutes BETWEEN 1 AND 150', name='ck_match_duration'),
        CheckConstraint("status IN ('scheduled','live','finished')", name='ck_match_status'),
    )


class MatchParticipant(Base):
    __tablename__ = 'match_participants'
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id', ondelete='CASCADE'), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id', ondelete='RESTRICT'), primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey('clubs.id', ondelete='RESTRICT'))


class MatchEvent(Base):
    __tablename__ = 'match_events'
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, index=True)
    player_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(20))
    minute: Mapped[int] = mapped_column(Integer)
    added_time: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    related_goal_id: Mapped[int | None] = mapped_column(ForeignKey('match_events.id', ondelete='RESTRICT'), unique=True)
    participant: Mapped[MatchParticipant] = relationship()
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(['match_id','player_id'], ['match_participants.match_id','match_participants.player_id'], ondelete='CASCADE'),
        CheckConstraint("event_type IN ('goal','assist','yellow_card','red_card')", name='ck_event_type'),
        CheckConstraint('minute BETWEEN 0 AND 150 AND added_time BETWEEN 0 AND 30', name='ck_event_time'),
    )

    @property
    def club_id(self): return self.participant.club_id
