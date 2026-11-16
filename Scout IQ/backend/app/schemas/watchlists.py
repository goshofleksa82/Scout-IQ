from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field,field_validator


class WatchlistValues(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=1000)


class WatchlistPlayer(BaseModel):
    model_config=ConfigDict(extra='forbid')
    player_id:int=Field(ge=1)


class WatchlistResponse(WatchlistValues):
    model_config=ConfigDict(from_attributes=True)
    id:int
    created_at:datetime
    updated_at:datetime
