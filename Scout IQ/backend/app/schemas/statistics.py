from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StatsValues(BaseModel):
    model_config = ConfigDict(extra='forbid')
    minutes_played: int = Field(ge=0, le=180)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    shots: int | None = Field(default=None, ge=0)
    passes_attempted: int | None = Field(default=None, ge=0)
    passes_completed: int | None = Field(default=None, ge=0)
    tackles: int | None = Field(default=None, ge=0)
    progressive_passes: int | None = Field(default=None, ge=0)
    progressive_carries: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def consistent(self):
        if self.shots is not None and self.goals > self.shots: raise ValueError('Goals cannot exceed shots')
        if self.passes_attempted is not None and self.passes_completed is not None and self.passes_completed > self.passes_attempted:
            raise ValueError('Completed passes cannot exceed attempted passes')
        actions = ('goals','assists','shots','passes_attempted','passes_completed','tackles','progressive_passes','progressive_carries')
        if self.minutes_played == 0 and any(getattr(self,key) not in (None,0) for key in actions):
            raise ValueError('Zero-minute records cannot contain playing actions')
        return self


class StatsCreate(StatsValues):
    player_id: int = Field(ge=1)


class StatsResponse(StatsCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    match_id: int
    updated_at: datetime
