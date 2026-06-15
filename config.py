import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]

EXCHANGE_SERVER: str = os.environ.get("EXCHANGE_SERVER", "mail.yektanet.com")
EXCHANGE_DOMAIN: str = os.environ.get("EXCHANGE_DOMAIN", "yektanet")

# Requesty (OpenAI-compatible AI proxy)
REQUESTY_API_KEY: str = os.environ["REQUESTY_API_KEY"]
REQUESTY_BASE_URL: str = os.environ.get("REQUESTY_BASE_URL", "https://router.requesty.ai/v1")
REQUESTY_MODEL: str = os.environ.get("REQUESTY_MODEL", "google/gemini-2.0-flash")

ENCRYPTION_KEY: bytes = os.environ["ENCRYPTION_KEY"].encode()

DB_PATH: str = os.environ.get("DB_PATH", "yektayar.db")

ADMIN_IDS: list[int] = [
    int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
]

# Exchange EWS endpoint (auto-discovered or explicit)
EXCHANGE_EWS_URL: str | None = os.environ.get("EXCHANGE_EWS_URL")

# Render / webhook settings
WEBHOOK_URL: str | None = os.environ.get("WEBHOOK_URL")
PORT: int = int(os.environ.get("PORT", "8443"))

# Pagination limits
EMAIL_PAGE_SIZE = 10
CALENDAR_DAYS_AHEAD = 7
