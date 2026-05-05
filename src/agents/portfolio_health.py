import json
import asyncio
from typing import AsyncIterable, List, Dict, Any
import yfinance as yf
from src.agents.base import BaseAgent
from src.models import UserProfile, IntentClassification, ChatMessage, ObservationsList
from src.llm import llm_client

class PortfolioHealthAgent(BaseAgent):
    async def run(
        self, 
        query: str, 
        user_profile: UserProfile, 
        intent: IntentClassification,
        history: List[ChatMessage]
    ) -> AsyncIterable[str]:
        
        # 1. Handle empty portfolio
        if not user_profile.positions:
            yield "data: " + json.dumps({"status": "processing", "message": "Analyzing your profile..."}) + "\n\n"
            yield "data: " + json.dumps({
                "observations": [
                    {"severity": "info", "text": "Your portfolio is currently empty. This is a great time to start building your first allocation!"}
                ],
                "advice": "Based on your risk profile, you might want to consider diversified low-cost ETFs as a starting point.",
                "disclaimer": "This is not investment advice. Please consult with a financial advisor before making any investment decisions."
            }) + "\n\n"
            return

        yield "data: " + json.dumps({"status": "processing", "message": "Fetching market data for your holdings..."}) + "\n\n"

        # 2. Fetch market data
        tickers = [p.ticker for p in user_profile.positions]
        # Map some common tickers if needed, or just use them as is. 
        # yfinance usually handles standard tickers well.
        
        market_data = {}
        try:
            # Batch fetch prices
            # Note: yfinance is synchronous, but we can wrap it or just call it if it's fast enough.
            # For this assignment, we'll assume it's acceptable or use a small wrapper.
            data = await asyncio.to_thread(yf.download, tickers, period="1y", interval="1d", progress=False)
            
            for ticker in tickers:
                if ticker in data['Close']:
                    current_price = data['Close'][ticker].iloc[-1]
                    start_price = data['Close'][ticker].iloc[0]
                    market_data[ticker] = {
                        "current_price": current_price,
                        "one_year_return": (current_price - start_price) / start_price if start_price != 0 else 0
                    }
                else:
                    # Fallback if ticker not found
                    market_data[ticker] = {"current_price": None, "one_year_return": 0}
        except Exception as e:
            yield "data: " + json.dumps({"status": "error", "message": f"Failed to fetch market data: {str(e)}"}) + "\n\n"
            # Continue with what we have (avg_cost)
            for p in user_profile.positions:
                market_data[p.ticker] = {"current_price": p.avg_cost, "one_year_return": 0}

        # 3. Calculate metrics
        total_value = 0
        portfolio_return = 0
        position_values = []
        
        for p in user_profile.positions:
            m = market_data.get(p.ticker, {"current_price": p.avg_cost})
            curr_price = m["current_price"] if m["current_price"] is not None else p.avg_cost
            val = p.quantity * curr_price
            total_value += val
            position_values.append({"ticker": p.ticker, "value": val})
            
            # Simple total return based on avg cost
            if p.avg_cost > 0:
                portfolio_return += ((curr_price - p.avg_cost) / p.avg_cost) * (val / 1.0) # Weighted return later

        # Weighted return
        if total_value > 0:
            weighted_return_sum = 0
            for p in user_profile.positions:
                if p.avg_cost > 0:
                    m = market_data.get(p.ticker, {})
                    curr_price = m.get("current_price")
                    if curr_price is None:
                        curr_price = p.avg_cost
                    
                    pos_val = p.quantity * curr_price
                    weighted_return_sum += ((curr_price - p.avg_cost) / p.avg_cost) * (pos_val / total_value)
            weighted_return = weighted_return_sum
        else:
            weighted_return = 0

        # Concentration
        position_values.sort(key=lambda x: x['value'], reverse=True)
        top_pos_pct = (position_values[0]['value'] / total_value * 100) if total_value > 0 else 0
        top_3_pos_pct = (sum(v['value'] for v in position_values[:3]) / total_value * 100) if total_value > 0 else 0
        
        concentration_flag = "low"
        if top_pos_pct > 40 or top_3_pos_pct > 70:
            concentration_flag = "high"
        elif top_pos_pct > 20 or top_3_pos_pct > 50:
            concentration_flag = "medium"

        # Benchmark comparison
        benchmark_ticker = "^GSPC" # S&P 500
        pref_bench = user_profile.preferences.preferred_benchmark
        if pref_bench == "QQQ": benchmark_ticker = "QQQ"
        elif pref_bench == "FTSE 100": benchmark_ticker = "^FTSE"
        
        bench_data = await asyncio.to_thread(yf.download, benchmark_ticker, period="1y", interval="1d", progress=False)
        bench_return = (bench_data['Close'].iloc[-1] - bench_data['Close'].iloc[0]) / bench_data['Close'].iloc[0] if not bench_data.empty else 0
        
        health_data = {
            "concentration_risk": {
                "top_position_pct": round(top_pos_pct, 2),
                "top_3_positions_pct": round(top_3_pos_pct, 2),
                "flag": concentration_flag
            },
            "performance": {
                "total_return_pct": round(weighted_return * 100, 2),
                "annualized_return_pct": round(weighted_return * 100, 2) # Simplified
            },
            "benchmark_comparison": {
                "benchmark": pref_bench or "S&P 500",
                "portfolio_return_pct": round(weighted_return * 100, 2),
                "benchmark_return_pct": round(float(bench_return) * 100, 2),
                "alpha_pct": round((weighted_return - float(bench_return)) * 100, 2)
            }
        }

        # 4. Generate observations using LLM
        yield "data: " + json.dumps({"status": "processing", "message": "Generating insights..."}) + "\n\n"
        
        prompt = f"""
Analyze the following portfolio health data for user {user_profile.name} (Risk Profile: {user_profile.risk_profile}).
Data: {json.dumps(health_data)}
Positions: {json.dumps([{"ticker": p.ticker, "qty": p.quantity} for p in user_profile.positions])}

Provide 2-3 concise observations in plain language. 
Include a severity (info, warning, success).
"""
        messages = [{"role": "system", "content": "You are a financial health expert. Be concise and professional."}, {"role": "user", "content": prompt}]
        
        try:
            obs_raw = await llm_client.get_structured_completion(messages, ObservationsList)
            observations = [o.model_dump() for o in obs_raw.observations]
        except Exception as e:
            # Fallback observations
            observations = [
                {"severity": "info" if concentration_flag == "low" else "warning", "text": f"Your top position accounts for {top_pos_pct:.1f}% of your portfolio."},
                {"severity": "success" if weighted_return > bench_return else "info", "text": f"Your portfolio return is {weighted_return*100:.1f}% compared to {bench_return*100:.1f}% for the benchmark."}
            ]

        health_data["observations"] = observations
        health_data["disclaimer"] = "This is not investment advice. All investing involves risk of loss. Past performance does not guarantee future results."

        # Final structured response
        yield "data: " + json.dumps(health_data) + "\n\n"
        yield "event: end\ndata: {}\n\n"

portfolio_health_agent = PortfolioHealthAgent()
