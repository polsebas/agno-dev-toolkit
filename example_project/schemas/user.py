# Correct pattern — for toolkit to confirm as valid
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    risk_score: int = Field(ge=1, le=10)


class SessionState(BaseModel):
    user: UserProfile
    intent: str
    turn_count: int = 0
