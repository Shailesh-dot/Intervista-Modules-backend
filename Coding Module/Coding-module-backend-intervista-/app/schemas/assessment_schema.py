from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AssessmentSessionCreate(BaseModel):
    candidate_id: str
    duration_minutes: int = 60

class AssessmentSessionResponse(BaseModel):
    session_id: str
    candidate_id: str
    status: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    
    model_config = ConfigDict(from_attributes=True)
