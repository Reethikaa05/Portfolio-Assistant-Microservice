from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import date

class Position(BaseModel):
    ticker: str
    exchange: str
    quantity: float
    avg_cost: float
    currency: str
    purchased_at: Optional[Union[str, date]] = None

class KYC(BaseModel):
    status: str

class UserPreferences(BaseModel):
    preferred_benchmark: Optional[str] = "S&P 500"

class UserProfile(BaseModel):
    user_id: str
    name: str
    age: int
    country: str
    base_currency: str
    kyc: KYC
    risk_profile: str
    positions: List[Position]
    preferences: UserPreferences

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    user_profile: UserProfile
    history: List[ChatMessage] = []

class IntentClassification(BaseModel):
    intent: str
    entities: Dict[str, Any] = {}
    target_agent: str
    safety_verdict: Optional[str] = None
    model_config = ConfigDict(extra='forbid')

class AgentResponse(BaseModel):
    agent_name: str
    content: Any
    metadata: Dict[str, Any] = {}

class Observation(BaseModel):
    severity: str
    text: str
    model_config = ConfigDict(extra='forbid')

class ObservationsList(BaseModel):
    observations: List[Observation]
    model_config = ConfigDict(extra='forbid')
