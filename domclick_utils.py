"""Поиск характеристик здания на Domclick (fallback / дополнение к МинЖКХ)."""

import json
import re
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from domclick_parse_dict import (
    BUILDING_FIELD_LABELS,
    BUILDING_FIELD_ORDER,
    CITY_SUBDOMAINS,
    DISTRICT_SLUGS,
    JSON_FIELD_KEYS,
    KNOWN_BUILDINGS,
    MICRODISTRICT_SLUGS,
    YEAR_JSON_KEYS,
    YEAR_PAGE_TEXT_RE,
    YEAR_VALUE_RE,
    normalize_field_label,
)
from house_utils import normalize_house_and_block, normalize_house_token
from settings import _env

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_DOMCLICK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    for word in ("район", "р-н", "микрорайон", "мкр", "ул", "улица"):
        text = text.replace(word, " ")
    chunks = []
    for char in text:
        if char in _TRANSLIT:
            chunks.append(_TRANSLIT[char])
        elif char.isascii() and char.isalnum():
            chunks.append(char)
        elif char in " -_":
            chunks.append("-")
    slug = "".join(chunks)
    return re.sub(r"-+", "-", slug).strip("-")


def _district_slug(city_district: Optional[str]) -> Optional[str]:
    if not city_district:
        return None
    key = city_district.lower().replace("район", "").replace("р-н", "").strip()
    if key in DISTRICT_SLUGS:
        return DISTRICT_SLUGS[key]
    return _slugify(city_district)


def _city_subdomain(city: Optional[str], settlement: Optional[str]) -> str:
    name = (city or settlement or "ufa").lower()
    return CITY_SUBDOMAINS.get(name, _slugify(name))


def _house_slug_part(house_num: str, block_num: Optional[str]) -> str:
    token = normalize_house_token(house_num).replace(" ", "")
    if block_num:
        return f"{token}-{block_num}"
    return token


def _address_cache_key(
    city: Optional[str],
    street: Optional[str],
    house_num: str,
    block_num: Optional[str],
) -> str:
    block = block_num or ""
    return f"{(city or '').lower()}|{street or ''}|{house_num}|{block}".lower()


def _known_building(cadastral_number: Optional[str]) -> Optional[dict]:
    if cadastral_number and cadastral_number in KNOWN_BUILDINGS:
        return KNOWN_BUILDINGS[cadastral_number]
    return None


def _known_slug(
    cadastral_number: Optional[str],
    city: Optional[str],
    street: Optional[str],
    house_num: str,
    block_num: Optional[str],
) -> Optional[str]:
    known = _known_building(cadastral_number)
    if known:
        return known.get("slug")
    key = _address_cache_key(city, street, house_num, block_num)
    entry = KNOWN_BUILDINGS.get(key)
    return entry.get("slug") if entry else None


def _slug_candidates(
    city: Optional[str],
    settlement: Optional[str],
    street: Optional[str],
    house_num: str,
    block_num: Optional[str],
    city_district: Optional[str],
    cadastral_number: Optional[str],
) -> list[str]:
    """Известный slug первым, затем авто-варианты (для дополнения к МинЖКХ)."""
    candidates: list[str] = []
    known = _known_slug(cadastral_number, city, street, house_num, block_num)
    if known:
        candidates.append(known)

    street_slug = _slugify(street or "")
    house_slug = _house_slug_part(house_num, block_num)
    district = _district_slug(city_district)

    if district and street_slug:
        for micro_slug in MICRODISTRICT_SLUGS.values():
            candidates.append(f"{district}--{micro_slug}--{street_slug}--{house_slug}")
        candidates.append(f"{district}--{street_slug}--{house_slug}")

    if street_slug:
        candidates.append(f"{street_slug}--{house_slug}")

    seen: set[str] = set()
    unique: list[str] = []
    for slug in candidates:
        if slug not in seen:
            seen.add(slug)
            unique.append(slug)
    return unique


def _set_field(fields: dict[str, str], code: str, value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text and code in BUILDING_FIELD_ORDER:
        fields[code] = text


def _fields_from_json(obj: Any, fields: dict[str, str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = re.sub(r"[^a-z0-9]", "", key.lower())
            if key_lower in YEAR_JSON_KEYS and value is not None:
                match = YEAR_VALUE_RE.search(str(value))
                if match:
                    _set_field(fields, "build_year", match.group(1))
            if key_lower in JSON_FIELD_KEYS and value is not None:
                _set_field(fields, JSON_FIELD_KEYS[key_lower], value)
            _fields_from_json(value, fields)
    elif isinstance(obj, list):
        for item in obj:
            _fields_from_json(item, fields)


def _fields_from_soup(soup: BeautifulSoup, fields: dict[str, str]) -> None:
    for dt in soup.find_all("dt"):
        label = normalize_field_label(dt.get_text())
        code = BUILDING_FIELD_LABELS.get(label)
        if not code:
            continue
        dd = dt.find_next_sibling("dd")
        if dd:
            _set_field(fields, code, dd.get_text(strip=True))

    for row in soup.find_all(["tr", "li", "div"]):
        text = row.get_text("\n", strip=True)
        if "\n" not in text or len(text) > 500:
            continue
        parts = text.split("\n", 1)
        if len(parts) != 2:
            continue
        label = normalize_field_label(parts[0])
        code = BUILDING_FIELD_LABELS.get(label)
        if code:
            _set_field(fields, code, parts[1])


def _extract_fields_from_html(html: str) -> dict[str, str]:
    if "__qrator" in html or len(html) < 1000:
        return {}

    fields: dict[str, str] = {}

    next_data = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if next_data:
        try:
            _fields_from_json(json.loads(next_data.group(1)), fields)
        except json.JSONDecodeError:
            pass

    soup = BeautifulSoup(html, "html.parser")
    _fields_from_soup(soup, fields)

    if "build_year" not in fields:
        page_match = YEAR_PAGE_TEXT_RE.search(html)
        if page_match:
            fields["build_year"] = page_match.group(1)

    return fields


def _merge_fields(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
    result = dict(base)
    for key, value in extra.items():
        if value and not result.get(key):
            result[key] = value
    return result


def _domclick_headers() -> dict[str, str]:
    headers = dict(_DOMCLICK_HEADERS)
    cookie = _env("DOMCLICK_COOKIE")
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _fetch_building_page(session: requests.Session, subdomain: str, slug: str) -> Optional[str]:
    url = f"https://{subdomain}.domclick.ru/building/{slug}"
    try:
        res = session.get(url, headers=_domclick_headers(), timeout=12)
        if res.status_code != 200:
            return None
        return res.text
    except Exception:
        return None


def get_building_from_domclick(
    cadastral_number: str,
    city: Optional[str],
    street: Optional[str],
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
    city_district: Optional[str] = None,
) -> tuple[dict[str, str], Optional[str]]:
    """Возвращает (поля здания, url карточки Domclick). Всегда пробует все slug."""
    house_num, block_num = normalize_house_and_block(house, block)
    if not street or not house_num:
        return {}, None

    subdomain = _city_subdomain(city, settlement)
    session = requests.Session()
    cad_key = cadastral_number if cadastral_number != "Не указан" else None
    known = _known_building(cad_key)
    merged: dict[str, str] = dict(known.get("fields") or {}) if known else {}
    best_url: Optional[str] = None
    if known and known.get("slug"):
        best_url = f"https://{subdomain}.domclick.ru/building/{known['slug']}"

    for slug in _slug_candidates(
        city, settlement, street, house_num, block_num, city_district, cad_key,
    ):
        page_url = f"https://{subdomain}.domclick.ru/building/{slug}"
        html = _fetch_building_page(session, subdomain, slug)
        if not html:
            continue
        parsed = _extract_fields_from_html(html)
        if parsed:
            merged = _merge_fields(merged, parsed)
            best_url = page_url

    if merged:
        return merged, best_url
    return {}, None


def get_year_from_domclick(
    cadastral_number: str,
    city: Optional[str],
    street: Optional[str],
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
    city_district: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Совместимость: (год, материал стен, url)."""
    fields, url = get_building_from_domclick(
        cadastral_number, city, street, house, block, settlement, city_district,
    )
    if not fields:
        return None, None, url
    return fields.get("build_year"), fields.get("wall_material"), url
