import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from src.models import ChatRequest, UserProfile, ChatMessage
from src.safety import safety_guard
from src.classifier import classifier
from src.agents.portfolio_health import portfolio_health_agent
from src.agents.general_query import general_query_agent
from src.agents.stub import stub_agent
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Valura AI Microservice")

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

AGENT_MAP = {
    "portfolio_health": portfolio_health_agent,
    "general_query": general_query_agent,
    "market_research": general_query_agent,
    "investment_strategy": general_query_agent,
    "financial_planning": general_query_agent,
    "risk_assessment": general_query_agent,
    "product_recommendation": general_query_agent,
    "predictive_analysis": general_query_agent,
}

@app.post("/chat")
async def chat(request: ChatRequest):
    async def event_generator():
        try:
            # 1. Safety Guard
            is_blocked, category, refusal = safety_guard.check_query(request.query)
            if is_blocked:
                yield {
                    "data": json.dumps({
                        "type": "error",
                        "error_type": "safety_violation",
                        "category": category,
                        "content": refusal
                    })
                }
                yield {"event": "end", "data": "{}"}
                return

            # 2. Intent Classifier
            yield {
                "data": json.dumps({"status": "classifying", "message": "Analyzing your request..."})
            }
            intent_result = await classifier.classify(
                request.query, 
                request.history, 
                request.user_profile
            )
            
            yield {
                "data": json.dumps({
                    "status": "routing",
                    "intent": intent_result.intent,
                    "target_agent": intent_result.target_agent,
                    "entities": intent_result.entities
                })
            }

            # 3. Route to Agent
            agent = AGENT_MAP.get(intent_result.target_agent, stub_agent)
            
            async for chunk in agent.run(
                request.query,
                request.user_profile,
                intent_result,
                request.history
            ):
                # The agent yields formatted SSE data strings like "data: {...}\n\n"
                # or "event: end\ndata: {}\n\n". We need to parse these for EventSourceResponse.
                lines = chunk.split('\n')
                event_type = None
                for line in lines:
                    line = line.strip()
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                    elif line.startswith("data: "):
                        data_content = line[6:].strip()
                        if event_type:
                            yield {"event": event_type, "data": data_content}
                            event_type = None
                        else:
                            yield {"data": data_content}
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            error_msg = "An internal error occurred while processing your request."
            
            if "insufficient_quota" in str(e).lower() or "429" in str(e):
                error_msg = "OpenAI API Quota Exceeded. Please check your billing details or provide a new API key in the .env file."
            elif "invalid_api_key" in str(e).lower() or "401" in str(e):
                error_msg = "Invalid OpenAI API Key. Please verify the key in your .env file."

            yield {
                "data": json.dumps({
                    "type": "error",
                    "content": error_msg
                })
            }
            yield {"event": "end", "data": "{}"}

    return EventSourceResponse(event_generator())

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
