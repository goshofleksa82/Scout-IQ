from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

DATABASE_URL = settings.database_url
engine = create_engine(DATABASE_URL,pool_pre_ping=True,pool_size=5,max_overflow=5,pool_recycle=1800,connect_args={'connect_timeout':5})

SessionLocal = sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine
)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
