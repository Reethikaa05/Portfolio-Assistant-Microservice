import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.agents.portfolio_health import portfolio_health_agent
from src.models import UserProfile, IntentClassification, ObservationsList, Observation

async def collect_agent_response(user_dict):
    user_profile = UserProfile(**user_dict)
    intent = IntentClassification(intent="portfolio_health", target_agent="portfolio_health")
    
    # Mock yfinance and LLM to avoid network calls
    with patch("yfinance.download") as mock_yf, \
         patch("src.agents.portfolio_health.llm_client.get_structured_completion", new_callable=AsyncMock) as mock_complete:
        
        # Mock yfinance return data
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__getitem__.return_value.iloc.__getitem__.return_value = 150.0 # Price
        mock_yf.return_value = mock_df
        
        mock_complete.return_value = ObservationsList(observations=[
            Observation(severity="info", text="Test observation")
        ])

        chunks = []
        async for chunk in portfolio_health_agent.run("test query", user_profile, intent, []):
            if chunk.startswith("data: "):
                data = json.loads(chunk[6:].strip())
                chunks.append(data)
        
        # Find the final data chunk
        for chunk in reversed(chunks):
            if "disclaimer" in chunk:
                return chunk
    return None

@pytest.mark.asyncio
async def test_portfolio_health_does_not_crash_on_empty_portfolio(load_user):
    """user_004 has no positions. Agent must not crash."""
    user = load_user("usr_004")
    response = await collect_agent_response(user)

    assert response is not None
    assert "disclaimer" in response

@pytest.mark.asyncio
async def test_portfolio_health_flags_concentration(load_user):
    """user_003 has ~60% in NVDA. Agent must surface this."""
    user = load_user("usr_003")
    response = await collect_agent_response(user)

    assert response["concentration_risk"]["flag"] in {"high", "warning", "medium"}

@pytest.mark.asyncio
async def test_portfolio_health_includes_disclaimer(load_user):
    user = load_user("usr_001")
    response = await collect_agent_response(user)
    assert response["disclaimer"]
    assert "not investment advice" in response["disclaimer"].lower()
