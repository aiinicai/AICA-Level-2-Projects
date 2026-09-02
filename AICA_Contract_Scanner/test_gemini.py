import os
from dotenv import load_dotenv
from google import genai

print("1. Starting Gemini test...")

load_dotenv()

print("2. .env file loaded")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("3. ERROR: GEMINI_API_KEY was not found.")
    raise SystemExit

print("3. API key found")

try:
    client = genai.Client(api_key=api_key)

    print("4. Gemini client created")

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Reply with exactly: Gemini connection successful"
    )

    print("5. Gemini responded")

    print("Response:")
    print(response.text)

except Exception as e:
    print("ERROR:")
    print(type(e).__name__)
    print(str(e))