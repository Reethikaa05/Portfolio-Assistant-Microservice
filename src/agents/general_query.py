import json
from typing import AsyncIterable, List
from src.agents.base import BaseAgent
from src.models import UserProfile, IntentClassification, ChatMessage
from src.llm import llm_client

class GeneralQueryAgent(BaseAgent):
    async def run(
        self, 
        query: str, 
        user_profile: UserProfile, 
        intent: IntentClassification,
        history: List[ChatMessage]
    ) -> AsyncIterable[str]:
        
        system_prompt = f"""
You are Valura AI, a helpful AI wealth management assistant.
The user is {user_profile.name} from {user_profile.country}.
Risk Profile: {user_profile.risk_profile}.

Answer the user's query professionally and educationally. 
If they ask for definitions or general financial knowledge, be clear and concise.
Always include a regulatory disclaimer at the end.
"""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": query})

        full_content = ""
        async for chunk in llm_client.stream_completion(messages):
            full_content += chunk
            yield "data: " + json.dumps({"type": "content", "delta": chunk}) + "\n\n"
        
        yield "data: " + json.dumps({
            "type": "metadata",
            "disclaimer": "This is for educational purposes only and does not constitute financial advice."
        }) + "\n\n"
        yield "event: end\ndata: {}\n\n"

general_query_agent = GeneralQueryAgent()
