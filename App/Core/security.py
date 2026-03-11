from typing import Optional

from fastapi import Header, HTTPException

from App.Core.config import API_KEY


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")