import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "economy")

# empty means connect to telegram directly
PROXY_URL = os.getenv("PROXY_URL") or None


def require_bot_token() -> str:
    """Checked when the bot starts, so tests can import config without a token."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    return BOT_TOKEN
