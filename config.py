import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "bot_data.db")))

# API Keys & Tokens (loaded from .env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Gemini Models (Fast, primary)
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest"
]

# OpenRouter Models (High quality Russian, no Chinese models)
OPENROUTER_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "recursive/flint-v1.0:free",
    "dots-studio/dots-3-note-preview:free"
]

# History settings: 100 messages (50 user + 50 bot replies)
MAX_HISTORY_TURNS = 100
