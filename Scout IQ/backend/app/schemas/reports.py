from datetime import date,datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field


class ReportValues(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    title:str=Field(min_length=1,max_length=150)
    observed_on:date|None=None
    context:str=Field(default='',max_length=1000)
    technical:str=Field(default='',max_length=4000)
    tactical:str=Field(default='',max_length=4000)
    physical:str=Field(default='',max_length=4000)
    mental:str=Field(default='',max_length=4000)
    summary:str=Field(default='',max_length=4000)
    recommendation:Literal['observe','follow_up','shortlist','not_now']='observe'


class ReportCreate(ReportValues):
    player_id:int=Field(ge=1)


class ReportEdit(ReportValues):
    expected_version:int=Field(ge=1)


class ReportResponse(ReportValues):
    model_config=ConfigDict(from_attributes=True)
    id:int
    player_id:int
    author_id:int
    version:int
    created_at:datetime
    updated_at:datetime
