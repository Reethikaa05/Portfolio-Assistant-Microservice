import requests
import json

url = "http://localhost:8000/chat"
payload = {
    "query": "hello",
    "user_profile": {
        "user_id": "usr_001",
        "name": "Alex Chen",
        "age": 30,
        "country": "US",
        "base_currency": "USD",
        "kyc": {"status": "verified"},
        "risk_profile": "aggressive",
        "positions": [],
        "preferences": {"preferred_benchmark": "S&P 500"}
    },
    "history": []
}

response = requests.post(url, json=payload, stream=True)
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
