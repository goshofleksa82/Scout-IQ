
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)
    position: Mapped[str] = mapped_column(String(10), nullable=False)
    club: Mapped[str] = mapped_column(String(100), nullable=False)
    goals: Mapped[int] = mapped_column(nullable=False)
    assists: Mapped[int] = mapped_column(nullable=False)
    minutes_played: Mapped[int] = mapped_column(nullable=False)
