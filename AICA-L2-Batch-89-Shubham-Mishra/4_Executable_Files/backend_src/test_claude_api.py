"""
Quick connectivity check for the Anthropic Claude API.
Run: python src/test_claude_api.py
Reads ANTHROPIC_API_KEY from .env (never hardcode the key here).
"""
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

key = os.getenv("ANTHROPIC_API_KEY", "")
if not key or key == "your-anthropic-api-key-here":
    raise SystemExit(
        "ANTHROPIC_API_KEY is not set in .env. "
        "Copy .env.example to .env and paste your real key (starts with sk-ant-)."
    )

client = anthropic.Anthropic(api_key=key)
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=50,
    messages=[{"role": "user", "content": "Reply with exactly: API connection OK"}],
)
print(response.content[0].text)
