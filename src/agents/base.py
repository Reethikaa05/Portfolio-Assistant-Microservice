from abc import ABC, abstractmethod
from typing import AsyncIterable, Dict, Any
from src.models import UserProfile, IntentClassification, ChatMessage

class BaseAgent(ABC):
    @abstractmethod
    async def run(
        self, 
        query: str, 
        user_profile: UserProfile, 
        intent: IntentClassification,
        history: list[ChatMessage]
    ) -> AsyncIterable[str]:
        pass
