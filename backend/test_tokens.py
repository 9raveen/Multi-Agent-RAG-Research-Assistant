from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv() 

client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
resp = client.chat.completions.with_raw_response.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "hi"}],
    max_tokens=5,
)
print("Remaining tokens:", resp.headers.get("x-ratelimit-remaining-tokens"))
print("Resets in:", resp.headers.get("x-ratelimit-reset-tokens"))