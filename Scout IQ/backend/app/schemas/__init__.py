"""Pydantic v2 response contracts for ScoutIQ."""
from pydantic import (
    BaseModel, ConfigDict, Field, EmailStr, SecretStr,
    field_validator, model_validator)
from typing import Literal

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
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


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
    name: str = Field(min_length=1,max_length=100)
    age: int = Field(ge=0)
    position: str = Field(min_length=1,max_length=10)
    club: str = Field(min_length=1,max_length=100)
    club_id: int | None = Field(default=None, ge=1)
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
    club_id: int | None = Field(default=None, ge=1)
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

class UserIdentity(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    model_config = ConfigDict(extra="forbid")

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not value.isascii() or not all(
            c.isalnum() or c == "_" for c in value
        ):
            raise ValueError(
                "Username must contain only ASCII letters, "
                "numbers, or underscores"
            )

        return value


class UserCreate(UserIdentity):
    email: EmailStr = Field(max_length=255)
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("Password cannot be blank")
        return value


class UserResponse(BaseModel):
    id: int = Field(ge=1)
    username: str
    email: EmailStr
    role: Literal["viewer", "admin"]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(UserIdentity):
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, data):
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("Profile fields cannot be null")
        return data

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return UserIdentity.normalize_username(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        return UserIdentity.validate_username(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return UserCreate.normalize_email(value)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def reject_blank(cls, value):
        return UserCreate.reject_blank_password(value)


class PlayerSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=100)
    club: str | None = Field(default=None, min_length=1, max_length=100)
    position: str | None = Field(default=None, min_length=1, max_length=10)
    min_age: int | None = Field(default=None, ge=0)
    max_age: int | None = Field(default=None, ge=0)
    min_goals: int | None = Field(default=None, ge=0)
    max_goals: int | None = Field(default=None, ge=0)
    min_assists: int | None = Field(default=None, ge=0)
    max_assists: int | None = Field(default=None, ge=0)
    min_minutes: int | None = Field(default=None, ge=0)
    max_minutes: int | None = Field(default=None, ge=0)
    sort_by: Literal["id", "name", "age", "goals", "assists", "minutes_played"] = "id"
    order: Literal["asc", "desc"] = "asc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("name", "club", "position", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def check_ranges(self):
        for name in ("age", "goals", "assists", "minutes"):
            low, high = getattr(self, "min_" + name), getattr(self, "max_" + name)
            if low is not None and high is not None and low > high:
                raise ValueError("Minimum " + name + " cannot exceed maximum")
        return self
