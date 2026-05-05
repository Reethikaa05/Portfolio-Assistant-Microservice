import json
from typing import AsyncIterable, List
from src.agents.base import BaseAgent
from src.models import UserProfile, IntentClassification, ChatMessage

class StubAgent(BaseAgent):
    async def run(
        self, 
        query: str, 
        user_profile: UserProfile, 
        intent: IntentClassification,
        history: List[ChatMessage]
    ) -> AsyncIterable[str]:
        yield "data: " + json.dumps({"type": "content", "delta": f"The '{intent.target_agent}' agent is not yet implemented in this build."}) + "\n\n"
        yield "event: end\ndata: {}\n\n"

stub_agent = StubAgent()
