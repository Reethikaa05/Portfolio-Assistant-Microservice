import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

try:
    print("Listing models...")
    for m in client.models.list():
        print(f"Name: {m.name}")
except Exception as e:
    print("Error:", str(e))
