
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity, Index, Integer, String, event, func, select, text, true, false
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy import inspect as inspect_orm
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.postgresql import ExcludeConstraint


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)
    position: Mapped[str] = mapped_column(String(10), nullable=False)
    club: Mapped[str] = mapped_column(String(100), nullable=False)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), index=True)
    current_club: Mapped[Club] = relationship(back_populates="players")
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey('import_batches.id',ondelete='RESTRICT'))
    goals: Mapped[int] = mapped_column(nullable=False)
    assists: Mapped[int] = mapped_column(nullable=False)
    minutes_played: Mapped[int] = mapped_column(nullable=False)

    # Match the existing PostgreSQL table; migrations must preserve these.
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        CheckConstraint("goals >= 0", name="players_goals_check"),
        CheckConstraint("assists >= 0", name="players_assists_check"),
        CheckConstraint("minutes_played >= 0", name="players_minutes_played_check"),
        Index("ix_players_position_club_age", func.lower(position), func.lower(club), age),
        Index("ix_players_club_lower", func.lower(club)),
        Index("ix_players_age", age),
        Index("ix_players_goals", goals),
        Index("ix_players_assists", assists),
        Index("ix_players_minutes_played", minutes_played),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)

    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="viewer", server_default="viewer"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    analytics_opt_in: Mapped[bool] = mapped_column(Boolean,default=False,server_default=false())
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "role IN ('viewer', 'admin')",
            name="ck_users_valid_role"
        ),
        CheckConstraint("token_version >= 0", name="ck_users_token_version"),
    )


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[str | None] = mapped_column(String(36))


class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    clubs: Mapped[list[Club]] = relationship(back_populates="competition", passive_deletes=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_competitions_name"),
        Index("uq_competitions_name_country", func.lower(name), func.lower(func.coalesce(country, "")), unique=True),
    )


class Club(Base):
    __tablename__ = "clubs"
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), index=True)
    competition: Mapped[Competition | None] = relationship(back_populates="clubs")
    players: Mapped[list[Player]] = relationship(back_populates="current_club", passive_deletes=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_clubs_name"),
        Index("uq_clubs_name_country", func.lower(name), func.lower(func.coalesce(country, "")), unique=True),
    )


class Season(Base):
    __tablename__ = "seasons"
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="ck_seasons_dates"),
        Index("uq_seasons_name", func.lower(name), unique=True),
    )


class Membership(Base):
    __tablename__ = "player_club_memberships"
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"), index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"), index=True)
    previous_club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="RESTRICT"), index=True)
    joined_on: Mapped[date] = mapped_column(Date)
    left_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

    __table_args__ = (
        CheckConstraint("left_on IS NULL OR left_on > joined_on", name="ck_membership_dates"),
        ExcludeConstraint((player_id, "="), (func.daterange(joined_on, left_on, text("'[)'")), "&&"),
                          name="ex_membership_overlap", using="gist"),
    )


@event.listens_for(Session, "before_flush")
def resolve_legacy_player_clubs(db, flush_context, instances):
    """Keep legacy club-name writes compatible with required relational clubs.

    Unknown countries remain NULL. A PostgreSQL upsert handles concurrent legacy
    name writes; all changes belong to the caller's transaction.
    """
    for player in list(db.new) + list(db.dirty):
        if not isinstance(player, Player): continue
        state = inspect_orm(player)
        if state.attrs.current_club.history.has_changes() and player.current_club is not None:
            player.club = player.current_club.name
            continue
        if player.club_id is not None and state.attrs.club_id.history.has_changes():
            club = db.get(Club, player.club_id)
            if club is not None: player.club = club.name
            continue  # An invalid explicit ID is rejected by the foreign key.
        if player.club_id is None or state.attrs.club.history.has_changes():
            name = player.club.strip()
            db.execute(pg_insert(Club).values(name=name).on_conflict_do_nothing())
            club = db.scalar(select(Club).where(func.lower(Club.name) == name.lower(), Club.country.is_(None)))
            player.current_club = club


from app.models.matches import Match, MatchParticipant, MatchEvent
from app.models.statistics import PlayerMatchStats
from app.models.imports import ImportBatch, ImportIdentity
from app.models.scoring import ScoringModel
from app.models.watchlists import Watchlist,WatchlistItem
from app.models.reports import ScoutingReport,ScoutingReportVersion
from app.models.audit import AuditLog,DataQualityRun
from app.models.product import ProductEvent,BetaFeedback
