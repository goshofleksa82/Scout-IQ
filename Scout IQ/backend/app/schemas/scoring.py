from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.services.cohorts import POSITION_METRICS

Weight=Annotated[float,Field(gt=0,le=1,strict=True,allow_inf_nan=False)]


class ScoringModelCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    version:str=Field(pattern=r'^(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$')
    position_group:Literal['strikers','wingers','midfielders','defenders','goalkeepers']
    weights:dict[str,Weight]=Field(min_length=1,max_length=5)
    description:str=Field(default='Configurable statistical criteria; validate them for your scouting workflow.',min_length=1,max_length=1000)

    @field_validator('name','description',mode='before')
    @classmethod
    def strip(cls,value): return value.strip() if isinstance(value,str) else value

    @model_validator(mode='after')
    def valid_weights(self):
        if abs(sum(self.weights.values())-1)>1e-6: raise ValueError('Metric weights must sum to 1')
        if any(name not in POSITION_METRICS[self.position_group] for name in self.weights):
            raise ValueError('Weights contain a metric unsupported for this position group')
        return self


class ScoringModelResponse(ScoringModelCreate):
    model_config=ConfigDict(from_attributes=True)
    id:int
    created_at:datetime
