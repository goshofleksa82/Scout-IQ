from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

EventName=Literal['onboarding_completed','player_profile_viewed','comparison_opened','watchlist_created','report_created','report_updated','feedback_submitted']


class PreferencesUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    analytics_opt_in:bool
    onboarding_completed:bool|None=None


class FeatureEvent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    event:EventName


class FeedbackCreate(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    category:Literal['bug','usability','data','feature']
    area:Literal['onboarding','search','profile','comparison','watchlist','report','other']
    rating:int=Field(ge=1,le=5)
    message:str=Field(min_length=10,max_length=3000)
    follow_up:bool=False


class FeedbackReview(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    status:Literal['new','triaged','planned','done','wont_do']
    priority:Literal['low','medium','high','urgent']
    admin_note:str=Field(default='',max_length=2000)
