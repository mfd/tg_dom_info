import json
from pathlib import Path

COOKIES_FILE = Path(__file__).resolve().parent.parent / "domclick_cookies.txt"
MOBILE_AUTH_FILE = Path(__file__).resolve().parent.parent / "domclick_mobile_auth.json"


def save_cookie(cookie_str: str) -> None:
    COOKIES_FILE.write_text(cookie_str, encoding="utf-8")
    print(f"✅ Сохранено в {COOKIES_FILE}")


def save_mobile_auth(cookie: str = "", hash_header: str = "", timestamp: str = "") -> None:
    """Сохранить auth-данные мобильного API (из Charles/перехвата)."""
    current: dict = {}
    if MOBILE_AUTH_FILE.exists():
        try:
            current = json.loads(MOBILE_AUTH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if cookie:
        current["cookie"] = cookie
    if hash_header:
        current["hash"] = hash_header
    if timestamp:
        current["timestamp"] = timestamp
    MOBILE_AUTH_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Mobile auth сохранён в {MOBILE_AUTH_FILE}")
