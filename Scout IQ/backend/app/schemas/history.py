from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SeasonCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=30)
    starts_on: date
    ends_on: date

    @field_validator('name', mode='before')
    @classmethod
    def strip(cls, value): return value.strip() if isinstance(value, str) else value

    @model_validator(mode='after')
    def dates(self):
        if self.ends_on < self.starts_on: raise ValueError('Season end must follow its start')
        return self


class SeasonResponse(SeasonCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class MembershipCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    club_id: int = Field(ge=1)
    season_id: int = Field(ge=1)
    joined_on: date
    left_on: date | None = None

    @model_validator(mode='after')
    def dates(self):
        if self.left_on is not None and self.left_on <= self.joined_on:
            raise ValueError('Membership end must follow its start')
        return self


class MembershipResponse(MembershipCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    player_id: int
    previous_club_id: int | None


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    club_id: int = Field(ge=1)
    season_id: int = Field(ge=1)
    transfer_date: date
