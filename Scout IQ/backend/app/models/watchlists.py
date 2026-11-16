from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,Identity,Index,String,func,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.models import Base


class Watchlist(Base):
    __tablename__='watchlists'
    id:Mapped[int]=mapped_column(Identity(),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    name:Mapped[str]=mapped_column(String(100))
    description:Mapped[str]=mapped_column(String(1000),default='',server_default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    __table_args__=(Index('uq_watchlist_owner_name',user_id,func.lower(name),unique=True),CheckConstraint('length(trim(name)) > 0',name='ck_watchlist_name'),)


class WatchlistItem(Base):
    __tablename__='watchlist_items'
    watchlist_id:Mapped[int]=mapped_column(ForeignKey('watchlists.id',ondelete='CASCADE'),primary_key=True)
    player_id:Mapped[int]=mapped_column(ForeignKey('players.id',ondelete='RESTRICT'),primary_key=True,index=True)
    added_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
