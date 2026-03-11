import os


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", ""))
API_KEY = os.getenv("API_KEY", "")
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "100"))
MAX_LIMIT = int(os.getenv("MAX_LIMIT", "500"))

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not configured")