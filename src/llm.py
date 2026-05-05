import os
import json
import logging
from typing import List, Dict, Any, Optional, Type, TypeVar, AsyncIterable
import google.genai as genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class LLMClient:
    def __init__(self, model: str = "gemini-1.5-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        self.online = bool(api_key and api_key.strip())
        self.model = "gemini-3-flash-preview"
        if self.online:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    async def get_structured_completion(
        self, 
        messages: List[Dict[str, str]], 
        response_model: Type[T],
        temperature: float = 0.0
    ) -> T:
        if not self.online:
            return self._fallback_structured(response_model, messages)

        try:
            # Convert messages to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

            schema = response_model.model_json_schema()
            
            def strip_additional_props(s):
                if isinstance(s, dict):
                    s.pop("additionalProperties", None)
                    for v in s.values():
                        strip_additional_props(v)
                elif isinstance(s, list):
                    for item in s:
                        strip_additional_props(item)
            
            strip_additional_props(schema)

            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )
            result = json.loads(response.text)
            return response_model(**result)
        except Exception as e:
            print(f"GEMINI ERROR: {e}")
            logger.warning("Gemini fallback activated: %s", str(e))
            return self._fallback_structured(response_model, messages)

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> AsyncIterable[str]:
        if not self.online:
            async for chunk in self._fallback_stream(messages):
                yield chunk
            return

        try:
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

            response = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature
                )
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"GEMINI STREAM ERROR: {e}")
            logger.warning("Gemini stream fallback activated: %s", str(e))
            async for chunk in self._fallback_stream(messages):
                yield chunk

    def _fallback_structured(self, response_model: Type[T], messages: List[Dict[str, str]]) -> T:
        text = messages[-1]["content"] if messages else ""

        if response_model.__name__ == "IntentClassification":
            intent = "general_query"
            target_agent = "general_query"
            lowered = text.lower()
            if any(token in lowered for token in ["portfolio", "concentration", "performance", "holdings", "portfolio health", "positions"]):
                intent = "portfolio_health"
                target_agent = "portfolio_health"
            elif any(token in lowered for token in ["buy", "sell", "rebalance", "risk", "allocate", "advisor"]):
                intent = "general_query"
                target_agent = "general_query"
            return response_model(
                intent=intent,
                target_agent=target_agent,
                entities={},
                safety_verdict="offline-fallback"
            )

        if response_model.__name__ == "ObservationsList":
            from src.models import Observation
            obs = []
            if "portfolio" in text.lower():
                obs = [
                    Observation(severity="info", text="This portfolio appears to be in a demo fallback mode with simple health guidance."),
                    Observation(severity="warning", text="Live market insights are disabled because the Google API is unavailable.")
                ]
            else:
                obs = [
                    Observation(severity="info", text="Agent observations are not available in offline mode.")]
            return response_model(observations=obs)

        try:
            return response_model.model_validate({})
        except Exception:
            return response_model(**{})

    async def _fallback_stream(self, messages: List[Dict[str, str]]) -> AsyncIterable[str]:
        prompt = messages[-1]["content"] if messages else ""
        greeting = "I'm running in offline demo mode because the Google API is unavailable."
        yield greeting + " "
        if prompt:
            yield f"You asked: {prompt[:200]}"
        yield " The app is returning a safe fallback response that works without API quota."
        yield "\n\n"

llm_client = LLMClient()
