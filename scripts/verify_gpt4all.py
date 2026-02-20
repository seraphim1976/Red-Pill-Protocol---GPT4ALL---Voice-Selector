import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import red_pill.config as cfg

def verify():
    print("🔴 Verifying Red Pill <-> GPT4All Connection")
    print(f"   Base URL:   {cfg.OPENAI_BASE_URL}")
    print(f"   Model Name: {cfg.LLM_MODEL_NAME}")
    print(f"   API Key:    {cfg.OPENAI_API_KEY if cfg.OPENAI_API_KEY else '(None)'}")
    
    if not cfg.OPENAI_BASE_URL:
        print("\n❌ OPENAI_BASE_URL is not set. Please set it in .env")
        return

    try:
        client = OpenAI(
            base_url=cfg.OPENAI_BASE_URL,
            api_key=cfg.OPENAI_API_KEY or "dummy"
        )
        print("\n✅ OpenAI Client Initialized")
        
        print(f"\n📡 Attempting to connect to {cfg.OPENAI_BASE_URL}...")
        try:
            # Try a simple listing or chat completion
            client.models.list()
            print("✅ Connection Successful! Server is reachable.")
        except Exception as e:
            print(f"⚠️  Could not connect to server: {e}")
            print("   (This is expected if GPT4All is not currently running. If it is running, check the port.)")

    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")

if __name__ == "__main__":
    verify()
