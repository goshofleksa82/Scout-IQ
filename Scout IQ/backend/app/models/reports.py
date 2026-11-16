from datetime import datetime,date
from sqlalchemy import Date,DateTime,ForeignKey,Identity,Integer,String,Text,CheckConstraint,Index,func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.models import Base


class ScoutingReport(Base):
    __tablename__='scouting_reports'
    id:Mapped[int]=mapped_column(Identity(),primary_key=True)
    author_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    player_id:Mapped[int]=mapped_column(ForeignKey('players.id',ondelete='RESTRICT'),index=True)
    title:Mapped[str]=mapped_column(String(150))
    observed_on:Mapped[date|None]=mapped_column(Date)
    context:Mapped[str]=mapped_column(String(1000),default='',server_default='')
    technical:Mapped[str]=mapped_column(Text,default='',server_default='')
    tactical:Mapped[str]=mapped_column(Text,default='',server_default='')
    physical:Mapped[str]=mapped_column(Text,default='',server_default='')
    mental:Mapped[str]=mapped_column(Text,default='',server_default='')
    summary:Mapped[str]=mapped_column(Text,default='',server_default='')
    recommendation:Mapped[str]=mapped_column(String(20),default='observe',server_default='observe')
    version:Mapped[int]=mapped_column(Integer,default=1,server_default='1')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    __table_args__=(CheckConstraint('length(trim(title)) > 0',name='ck_report_title'),CheckConstraint('version >= 1',name='ck_report_version'),CheckConstraint("recommendation IN ('observe','follow_up','shortlist','not_now')",name='ck_report_recommendation'),Index('ix_reports_author_player','author_id','player_id'),)


class ScoutingReportVersion(Base):
    __tablename__='scouting_report_versions'
    report_id:Mapped[int]=mapped_column(ForeignKey('scouting_reports.id',ondelete='CASCADE'),primary_key=True)
    version:Mapped[int]=mapped_column(Integer,primary_key=True)
    content:Mapped[dict]=mapped_column(JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(CheckConstraint('version >= 1',name='ck_report_history_version'),)
