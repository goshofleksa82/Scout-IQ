"""Pydantic v2 response contracts for ScoutIQ."""
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    age: int = Field(ge=0)
    position: str = Field(min_length=1)
    club: str = Field(min_length=1)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    minutes_played: int = Field(ge=0)

    @field_validator('name', 'position', 'club')
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Must not be blank')
        return value


class PlayerListResponse(BaseModel):
    players: list[PlayerResponse]


class PlayerStatsResponse(BaseModel):
    player_id: int = Field(ge=1)
    name: str = Field(min_length=1)
    goals_per_90: float = Field(ge=0)
    assists_per_90: float = Field(ge=0)
    goal_contributions_per_90: float = Field(ge=0)


class PlayerComparisonStats(BaseModel):
    name: str = Field(min_length=1)
    club: str = Field(min_length=1)
    position: str = Field(min_length=1)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    minutes_played: int = Field(ge=0)
    goals_per_90: float | None
    assists_per_90: float | None
    goal_contributions_per_90: float | None


class PlayerComparisonResponse(BaseModel):
    player1: PlayerComparisonStats
    player2: PlayerComparisonStats


class PlayerRankingEntry(BaseModel):
    rank: int = Field(ge=1)
    player_id: int = Field(ge=1)
    name: str = Field(min_length=1)
    position: str = Field(min_length=1)
    value: float = Field(ge=0)


class PlayerRankingsResponse(BaseModel):
    metric: str
    rankings: list[PlayerRankingEntry]

class PlayerCreate(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(ge=0)
    position: str = Field(min_length=1)
    club: str = Field(min_length=1)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    minutes_played: int = Field(ge=0)

    @field_validator("name", "position", "club")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be blank")

        return value

class PlayerUpdate(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=0)
    position: str | None = None
    club: str | None = None
    goals: int | None = Field(default=None, ge=0)
    assists: int | None = Field(default=None, ge=0)
    minutes_played: int | None = Field(default=None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null(cls, data):
        if isinstance(data, dict):
            for field, value in data.items():
                if field in cls.model_fields and value is None:
                    raise ValueError(
                        f"{field} cannot be null"
                    )
        return data

    @field_validator("name", "position", "club")
    @classmethod
    def reject_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Field cannot be blank")

        return value
