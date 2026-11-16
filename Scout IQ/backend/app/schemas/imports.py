from pydantic import BaseModel, Field, field_validator
from app.schemas import PlayerCreate
from app.schemas.matches import MatchCreate
from app.schemas.statistics import StatsCreate


class ExternalRecord(BaseModel):
    external_id: str=Field(min_length=1,max_length=128)

    @field_validator('external_id',mode='before')
    @classmethod
    def strip(cls,value): return value.strip() if isinstance(value,str) else value


class ImportPlayer(PlayerCreate,ExternalRecord): pass
class ImportMatch(MatchCreate,ExternalRecord): pass
class ImportStatistics(StatsCreate,ExternalRecord):
    match_id: int=Field(ge=1)
