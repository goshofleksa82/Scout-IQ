from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    position = Column(String(10), nullable=False)
    club = Column(String(100), nullable=False)
    goals = Column(Integer, nullable=False)
    assists = Column(Integer, nullable=False)
    minutes_played = Column(Integer, nullable=False)