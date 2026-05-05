import requests
import json

url = "http://localhost:8000/chat"
payload = {
    "query": "Tell me about the market today",
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
        line_str = line.decode('utf-8')
        if line_str.startswith("data: "):
            try:
                data = json.loads(line_str[6:])
                if "delta" in data:
                    print(data["delta"], end="", flush=True)
                else:
                    print(f"\n[DEBUG] {data}")
            except:
                print(f"\n[DEBUG] {line_str}")
        else:
            print(f"\n[DEBUG] {line_str}")
