from typing import List, Dict, Any, Optional
from src.llm import llm_client
from src.models import IntentClassification, ChatMessage, UserProfile
import json

class IntentClassifier:
    def __init__(self):
        self.system_prompt = """
You are the intent classifier for Valura AI, a wealth management platform.
Your job is to analyze the user's query and extract the intent, entities, and the target agent to handle the request.

### Agent Taxonomy:
- portfolio_health: structured assessment of the user's portfolio (concentration, performance, benchmarking, observations)
- market_research: factual/recent info about an instrument, sector, or market event
- investment_strategy: advice/strategy questions: should I buy/sell/rebalance, allocation guidance
- financial_planning: long-term planning: retirement, goals, savings rate
- financial_calculator: deterministic numerical computation: DCA returns, mortgage, tax, future value, FX conversion
- risk_assessment: risk metrics, exposure analysis, what-if scenarios
- product_recommendation: recommend specific products/funds matching user profile
- predictive_analysis: forward-looking analysis: forecasts, trend extrapolation
- customer_support: platform issues, account questions, how-to-use-app
- general_query: educational, conversational, definitions, greetings, or when no other agent fits

### Entity Vocabulary:
- tickers: array of strings, uppercase, exchange-suffixed where relevant (AAPL, ASML.AS, 7203.T)
- amount: number
- currency: ISO 4217 string (USD, EUR, GBP, JPY)
- rate: decimal (0.08 for 8%)
- period_years: integer
- frequency: one of: daily, weekly, monthly, yearly
- horizon: string token (6_months, 1_year, 5_years)
- time_period: string token (today, this_week, this_month, this_year)
- topics: array of strings
- sectors: array of strings
- index: string (S&P 500, FTSE 100, NIKKEI 225, MSCI World)
- action: one of: buy, sell, hold, hedge, rebalance
- goal: one of: retirement, education, house, FIRE, emergency_fund

### Instructions:
1. Identify the primary intent. If multiple intents exist, pick the most relevant one based on the context.
2. Extract all relevant entities according to the vocabulary.
3. Normalize entities (e.g., tickers should be uppercase, rates should be decimals).
4. Provide an informational safety verdict if the query seems borderline but was not blocked by the guard.
5. Consider the conversation history for follow-up queries (e.g., "what about Apple?" after "tell me about Microsoft").
6. If the query is ambiguous or missing parameters, still classify it but note the missing info in entities if possible.

Return a JSON object matching the IntentClassification schema.
"""

    async def classify(self, query: str, history: List[ChatMessage], user_profile: UserProfile) -> IntentClassification:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"User Context: {user_profile.model_dump_json()}"}
        ]
        
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
            
        messages.append({"role": "user", "content": query})
        
        try:
            result = await llm_client.get_structured_completion(
                messages=messages,
                response_model=IntentClassification
            )
            return result
        except Exception as e:
            # Fallback behavior
            return IntentClassification(
                intent="general_query",
                target_agent="general_query",
                entities={},
                safety_verdict=f"Error in classification: {str(e)}"
            )

classifier = IntentClassifier()
