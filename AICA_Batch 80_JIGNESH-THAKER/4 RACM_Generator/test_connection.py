import requests

# This is the address LM Studio gave you earlier
url = "http://127.0.0.1:1234/v1/chat/completions"

# The message we're sending to test the connection
payload = {
    "model": "qwen2.5-7b-instruct",
    "messages": [
        {"role": "user", "content": "Reply with exactly one sentence confirming you are working."}
    ],
    "temperature": 0.3
}

response = requests.post(url, json=payload)
result = response.json()

print("AI replied:")
print(result["choices"][0]["message"]["content"])