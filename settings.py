"""Секреты и ключи API — только из переменных окружения / .env."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value else None


BOT_TOKEN = _env("BOT_TOKEN")
DADATA_API = _env("DADATA_API")
DADATA_SECRET = _env("DADATA_SECRET")


def require_bot_token() -> str:
    if not BOT_TOKEN:
        raise ValueError("Переменная BOT_TOKEN не задана в .env")
    return BOT_TOKEN


def require_dadata_api() -> str:
    if not DADATA_API:
        raise ValueError("Переменная DADATA_API не задана в .env")
    return DADATA_API


def require_dadata_secret() -> Optional[str]:
    return DADATA_SECRET
