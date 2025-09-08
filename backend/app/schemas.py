from pydantic import BaseModel
from typing import Dict, Any

class GeneratePlanRequest(BaseModel):
    email: str
    regenerate: bool = False

class LearningPlanResponse(BaseModel):
    user_id: str
    model: str
    plan: Dict[str, Any]

class GoogleTokenIn(BaseModel):
    id_token: str