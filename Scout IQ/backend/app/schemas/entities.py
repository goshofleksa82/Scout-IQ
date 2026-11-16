from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    country: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator('name', 'country', mode='before')
    @classmethod
    def strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class CompetitionResponse(EntityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ClubCreate(EntityCreate):
    competition_id: int | None = Field(default=None, ge=1)


class ClubResponse(ClubCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
