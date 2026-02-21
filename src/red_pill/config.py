import os
from dotenv import load_dotenv

# Load environment variables if .env exists
load_dotenv()

# Qdrant Configuration
QDRANT_MODE = os.getenv("QDRANT_MODE", "embedded") # Options: "embedded", "server"

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_SCHEME = os.getenv("QDRANT_SCHEME", "http")
QDRANT_URL = f"{QDRANT_SCHEME}://{QDRANT_HOST}:{QDRANT_PORT}"
QDRANT_PATH = os.getenv("QDRANT_PATH", "local_qdrant_db_v2") # Local path for embedded mode

# Model Configuration (FastEmbed)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "384"))

# B760 Logic Configuration
DECAY_STRATEGY = os.getenv("DECAY_STRATEGY", "linear")  # Options: linear, exponential
if DECAY_STRATEGY not in ("linear", "exponential"):
    raise ValueError(f"Invalid DECAY_STRATEGY: {DECAY_STRATEGY}. Must be 'linear' or 'exponential'.")
EROSION_RATE = float(os.getenv("EROSION_RATE", "0.05"))
REINFORCEMENT_INCREMENT = float(os.getenv("REINFORCEMENT_INCREMENT", "0.1"))
PROPAGATION_FACTOR = float(os.getenv("PROPAGATION_FACTOR", "0.5"))  # Reinforcement fraction for associations
IMMUNITY_THRESHOLD = float(os.getenv("IMMUNITY_THRESHOLD", "10.0"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")

# Hugging Face Configuration (Free Image Generation)
HF_API_KEY = os.getenv("HF_API_KEY", "").strip() if os.getenv("HF_API_KEY") else None

# Fallback for Local LLM
if OPENAI_BASE_URL and not OPENAI_API_KEY:
    OPENAI_API_KEY = "dummy"

# Deep Recall Configuration
DEEP_RECALL_TRIGGERS = [
    "don't you remember",
    "¿no te acuerdas?",
    "deep recall",
    "do you really not remember?",
    "esfuerzate en recordar",
    "try hard!" # Tightened with exclamation mark to avoid accidental overlap
]
