from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,Identity,String,Text,Integer,Boolean,CheckConstraint,Index,func,false
from sqlalchemy.orm import Mapped,mapped_column
from app.models import Base


class ProductEvent(Base):
    __tablename__='product_events'
    id:Mapped[int]=mapped_column(Identity(),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    event:Mapped[str]=mapped_column(String(40),index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
    __table_args__=(CheckConstraint("event IN ('onboarding_completed','player_profile_viewed','comparison_opened','watchlist_created','report_created','report_updated','feedback_submitted')",name='ck_product_event_name'),)


class BetaFeedback(Base):
    __tablename__='beta_feedback'
    id:Mapped[int]=mapped_column(Identity(),primary_key=True)
    author_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    category:Mapped[str]=mapped_column(String(20))
    area:Mapped[str]=mapped_column(String(20))
    rating:Mapped[int]=mapped_column(Integer)
    message:Mapped[str]=mapped_column(Text)
    follow_up:Mapped[bool]=mapped_column(Boolean,default=False,server_default=false())
    status:Mapped[str]=mapped_column(String(20),default='new',server_default='new')
    priority:Mapped[str]=mapped_column(String(10),default='medium',server_default='medium')
    admin_note:Mapped[str]=mapped_column(Text,default='',server_default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    __table_args__=(CheckConstraint("category IN ('bug','usability','data','feature')",name='ck_feedback_category'),CheckConstraint("area IN ('onboarding','search','profile','comparison','watchlist','report','other')",name='ck_feedback_area'),CheckConstraint('rating BETWEEN 1 AND 5',name='ck_feedback_rating'),CheckConstraint("status IN ('new','triaged','planned','done','wont_do')",name='ck_feedback_status'),CheckConstraint("priority IN ('low','medium','high','urgent')",name='ck_feedback_priority'),)
