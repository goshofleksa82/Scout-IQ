from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class MatchCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    home_club_id: int = Field(ge=1)
    away_club_id: int = Field(ge=1)
    competition_id: int = Field(ge=1)
    season_id: int = Field(ge=1)
    kickoff_at: AwareDatetime
    duration_minutes: int = Field(default=90, ge=1, le=150)
    status: Literal['scheduled','live','finished'] = 'scheduled'

    @model_validator(mode='after')
    def distinct(self):
        if self.home_club_id == self.away_club_id: raise ValueError('Home and away clubs must differ')
        return self


class MatchResponse(MatchCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ParticipantCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    player_id: int = Field(ge=1)
    club_id: int = Field(ge=1)


class ParticipantResponse(ParticipantCreate):
    model_config = ConfigDict(from_attributes=True)
    match_id: int


class EventCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    player_id: int = Field(ge=1)
    event_type: Literal['goal','assist','yellow_card','red_card']
    minute: int = Field(ge=0, le=150)
    added_time: int = Field(default=0, ge=0, le=30)
    related_goal_id: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def assist_reference(self):
        if (self.event_type == 'assist') != (self.related_goal_id is not None):
            raise ValueError('Only assists require a related goal')
        return self


class EventResponse(EventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    match_id: int
    club_id: int


class MatchStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['scheduled','live','finished']
