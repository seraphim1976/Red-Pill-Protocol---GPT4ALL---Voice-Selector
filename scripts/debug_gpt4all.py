import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load env from repo root
repo_root = os.path.join(os.path.dirname(__file__), '..')
load_dotenv(os.path.join(repo_root, '.env'))

base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:4891/v1")
model_name = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
api_key = os.getenv("OPENAI_API_KEY", "dummy")

print(f"--- GPT4All Debugger ---")
print(f"URL: {base_url}")
print(f"Model: {model_name}")
print(f"API Key: {api_key[:5]}...")

try:
    client = OpenAI(base_url=base_url, api_key=api_key)
    
    # Simple non-streaming request
    print("\nSending request...")
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Hello, are you online?"}],
        stream=False
    )
    
    print("\n✅ Success!")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"\n❌ FAILED")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
