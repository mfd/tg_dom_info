"""Поиск характеристик здания на Domclick: мобильный API + HTML-скрапинг."""

import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

_COOKIES_FILE = Path(__file__).resolve().parent / "domclick_cookies.txt"
_MOBILE_AUTH_FILE = Path(__file__).resolve().parent / "domclick_mobile_auth.json"

_MOBILE_API_URL = "https://bff-search-mobile.domclick.ru/api/v2/ios/research_api/offers"
_SUGGEST_URL = "https://api.domclick.ru/my-home/geo-facade/api/v2/suggest"
_USER_REALTY_URL = "https://api.domclick.ru/my-home/api/v3/user_realty"
_SUGGEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru",
    "Origin": "https://domclick.ru",
    "Referer": "https://domclick.ru/",
}

_WALL_TYPE_MAP = {
    "panel": "Панельный",
    "brick": "Кирпичный",
    "monolith": "Монолитный",
    "wood": "Деревянный",
    "block": "Блочный",
    "monolith_brick": "Монолитно-кирпичный",
    "aerated_concrete": "Газобетонный",
    "foam_concrete": "Пенобетонный",
    "slag": "Шлакоблочный",
    "frame": "Каркасный",
}


def _load_cookie() -> Optional[str]:
    if _COOKIES_FILE.exists():
        text = _COOKIES_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def _load_mobile_auth() -> dict:
    if _MOBILE_AUTH_FILE.exists():
        try:
            return json.loads(_MOBILE_AUTH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

from domclick_parse_dict import (
    BUILDING_FIELD_LABELS,
    BUILDING_FIELD_ORDER,
    CITY_SUBDOMAINS,
    DISTRICT_SLUGS,
    JSON_FIELD_KEYS,
    KNOWN_BUILDINGS,
    MICRODISTRICT_SLUGS,
    STREET_SLUG_ALIASES,
    YEAR_JSON_KEYS,
    YEAR_PAGE_TEXT_RE,
    YEAR_VALUE_RE,
    normalize_field_label,
)
from house_utils import normalize_house_and_block, normalize_house_token

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_DOMCLICK_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


_STREET_TYPE_SLUGS: dict[str, str] = {
    "ул": "ulica", "улица": "ulica",
    "пр": "prospekt", "проспект": "prospekt",
    "пер": "pereulok", "переулок": "pereulok",
    "ш": "shosse", "шоссе": "shosse",
    "б-р": "bulvar", "бульвар": "bulvar",
    "пл": "ploshchad", "площадь": "ploshchad",
    "наб": "naberezhnaya", "набережная": "naberezhnaya",
    "туп": "tupik", "тупик": "tupik",
    "пр-д": "proezd", "проезд": "proezd",
    "ал": "alleya", "аллея": "alleya",
    "д": "doroga", "дорога": "doroga",
}

_SETTLEMENT_TYPE_SLUGS: dict[str, str] = {
    "г": "g", "город": "g",
    "с": "s", "село": "s",
    "пос": "pos", "поселок": "pos", "посёлок": "pos", "п": "pos",
    "д": "d", "деревня": "d",
    "рп": "rp", "рабочий поселок": "rp",
    "гп": "gp", "городской поселок": "gp",
    "пгт": "pgt",
    "х": "h", "хутор": "h",
    "аул": "aul",
    "ст": "stanitsya", "станица": "stanitsya",
}

_REGION_TYPE_SLUGS: dict[str, str] = {
    "респ": "respublika", "республика": "respublika",
    "обл": "oblast", "область": "oblast",
    "край": "kray",
    "ао": "avtonomnyj-okrug",
}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    for word in ("район", "р-н", "микрорайон", "мкр"):
        text = re.sub(rf"(^|\s){re.escape(word)}(\s|$)", " ", text)
    text = re.sub(r"^(ул|улица)\s+", "", text.strip())
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


def _settlement_slug_candidates(
    region: Optional[str],
    region_type: Optional[str],
    area: Optional[str],
    area_type: Optional[str],
    settlement_type: Optional[str],
    settlement: Optional[str],
    street_type: Optional[str],
    street: Optional[str],
    house_slug: str,
) -> list[str]:
    """Slug-кандидаты для сельских адресов: регион--район--тип-нп--тип-улица--дом."""
    if not settlement or not street or not house_slug:
        return []

    def _type_slug(abbr: Optional[str], lookup: dict) -> Optional[str]:
        if not abbr:
            return None
        return lookup.get(abbr.lower().rstrip("."), None)

    reg_type = _type_slug(region_type, _REGION_TYPE_SLUGS)
    reg_part = f"{reg_type}-{_slugify(region)}" if (region and reg_type) else (_slugify(region) if region else None)

    area_slug_raw = _slugify(area) if area else None
    area_type_word = _type_slug(area_type, {"р-н": "rajon", "район": "rajon", "р": "rajon"}) or "rajon"
    area_part = f"{area_slug_raw}-{area_type_word}" if area_slug_raw else None

    s_type = _type_slug(settlement_type, _SETTLEMENT_TYPE_SLUGS) or _slugify(settlement_type or "")
    s_part = f"{s_type}-{_slugify(settlement)}" if s_type else _slugify(settlement)

    st_type = _type_slug(street_type, _STREET_TYPE_SLUGS) or "ulica"
    st_part = f"{st_type}-{_slugify(street)}"

    candidates = []
    parts_full = [p for p in [reg_part, area_part, s_part, st_part, house_slug] if p]
    candidates.append("--".join(parts_full))

    # Без региона
    parts_no_reg = [p for p in [area_part, s_part, st_part, house_slug] if p]
    if len(parts_no_reg) < len(parts_full):
        candidates.append("--".join(parts_no_reg))

    # Без района
    parts_no_area = [p for p in [reg_part, s_part, st_part, house_slug] if p]
    if parts_no_area != parts_full:
        candidates.append("--".join(parts_no_area))

    return [c for c in dict.fromkeys(candidates) if c]  # dedupe, preserve order


def _street_slug(street: str) -> str:
    """Slug улицы для Domclick (без ломания «ул» в Губайдуллина)."""
    key = re.sub(r"\s+", " ", street.lower().strip())
    if key in STREET_SLUG_ALIASES:
        return STREET_SLUG_ALIASES[key]
    return _slugify(street)


def _district_slug(city_district: Optional[str]) -> Optional[str]:
    if not city_district:
        return None
    key = city_district.lower().replace("район", "").replace("р-н", "").strip()
    if key in DISTRICT_SLUGS:
        return DISTRICT_SLUGS[key]
    return _slugify(city_district)


def _city_subdomain(city: Optional[str], settlement: Optional[str]) -> str:
    if city:
        name = city.lower()
        return CITY_SUBDOMAINS.get(name, _slugify(name))
    # Rural settlements don't have their own Domclick subdomains — use ufa
    return "ufa"


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

    street_slug = _street_slug(street or "")
    house_slug = _house_slug_part(house_num, block_num)
    district = _district_slug(city_district)

    # Формат Domclick: ulica-minigali-gubajdullina--10-1
    if street_slug:
        candidates.append(f"ulica-{street_slug}--{house_slug}")

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

    # Next.js SSR
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

    # Client-side rendered pages: ищем данные о здании напрямую в JS-бандле
    # Находим фрагмент вида: "wallMaterial":"Кирпичный","builtYear":1959,"floors":6
    _extract_building_fields_from_js(html, fields)

    soup = BeautifulSoup(html, "html.parser")
    _fields_from_soup(soup, fields)

    if "build_year" not in fields:
        page_match = YEAR_PAGE_TEXT_RE.search(html)
        if page_match:
            fields["build_year"] = page_match.group(1)

    return fields


def _extract_building_fields_from_js(html: str, fields: dict[str, str]) -> None:
    """Извлекает поля здания из JS-бандла клиентских страниц Domclick."""
    # Ищем фрагмент с wallMaterial — он уникален для карточки здания
    m = re.search(r'"wallMaterial"\s*:\s*"([^"]{2,80})"', html)
    if m and not fields.get("wall_material"):
        _set_field(fields, "wall_material", m.group(1))

    # builtYear / buildYear рядом с wallMaterial — берём первый реалистичный
    for pat in (r'"builtYear"\s*:\s*(\d{4})', r'"buildYear"\s*:\s*(\d{4})'):
        ym = re.search(pat, html)
        if ym and YEAR_VALUE_RE.search(ym.group(1)) and not fields.get("build_year"):
            _set_field(fields, "build_year", ym.group(1))
            break

    # floors — ищем рядом с wallMaterial
    if m:
        ctx_start = max(0, m.start() - 200)
        ctx_end = min(len(html), m.end() + 200)
        ctx = html[ctx_start:ctx_end]
        fm = re.search(r'"floors"\s*:\s*(\d+)', ctx)
        if fm and not fields.get("floors"):
            _set_field(fields, "floors", fm.group(1))
        pm = re.search(r'"projectType"\s*:\s*"([^"]{2,60})"', ctx)
        if pm and not fields.get("building_series"):
            _set_field(fields, "building_series", pm.group(1))


def _merge_fields(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
    result = dict(base)
    for key, value in extra.items():
        if value and not result.get(key):
            result[key] = value
    return result


def is_qrator_blocked() -> bool:
    """Быстрая проверка — заблокирован ли Domclick Qrator-ом."""
    try:
        session = curl_requests.Session()
        headers = dict(_DOMCLICK_HEADERS)
        cookie = _load_cookie()
        if cookie:
            headers["Cookie"] = cookie
        res = session.get(
            "https://ufa.domclick.ru/", headers=headers, timeout=8, impersonate="chrome110"
        )
        return "__qrator" in res.text or res.status_code == 401
    except Exception:
        return True


def _fetch_building_page(session: curl_requests.Session, subdomain: str, slug: str) -> Optional[str]:
    url = f"https://{subdomain}.domclick.ru/building/{slug}"
    try:
        headers = dict(_DOMCLICK_HEADERS)
        cookie = _load_cookie() or _load_mobile_auth().get("cookie")
        if cookie:
            headers["Cookie"] = cookie
        res = session.get(url, headers=headers, timeout=12, impersonate="chrome110")
        if res.status_code != 200:
            return None
        if "__qrator" in res.text:
            logging.warning("Domclick: заблокирован Qrator, куки устарели или отсутствуют")
            return None
        return res.text
    except Exception:
        return None


def _suggest_building(query: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Публичный suggest API → (geo_guid, canonical_address, building_url) первого здания."""
    try:
        session = curl_requests.Session()
        res = session.get(
            _SUGGEST_URL,
            params={"query": query, "limit": 3},
            headers=_SUGGEST_HEADERS,
            timeout=8,
            impersonate="chrome110",
        )
        if res.status_code != 200:
            return None, None, None
        for item in (res.json().get("result") or []):
            if item.get("kind") == "house":
                geo_guid = item.get("geo_guid")
                address = item.get("address")
                # Пробуем извлечь slug/URL если suggest API возвращает seo-ссылку
                seo_uri = item.get("seo_uri") or item.get("uri") or item.get("url") or ""
                building_url = None
                if seo_uri and ".domclick.ru" in seo_uri:
                    building_url = seo_uri if seo_uri.startswith("http") else f"https://ufa.domclick.ru{seo_uri}"
                elif seo_uri and seo_uri.startswith("/building/"):
                    building_url = f"https://ufa.domclick.ru{seo_uri}"
                return geo_guid, address, building_url
    except Exception as exc:
        logging.debug("Domclick suggest: %s", exc)
    return None, None, None


def _combined_cookie() -> Optional[str]:
    """Объединяет browser cookie (Qrator+session) и mobile auth (CAS) в одну строку."""
    main = _load_cookie() or ""
    mobile = _load_mobile_auth().get("cookie") or ""
    if not main and not mobile:
        return None
    # Объединяем: mobile сначала (CAS), main дополняет (browser session + Qrator)
    combined: dict[str, str] = {}
    for part in (mobile + "; " + main).split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            combined.setdefault(k.strip(), v.strip())
    return "; ".join(f"{k}={v}" for k, v in combined.items()) or None


def _get_building_via_guid(geo_guid: str) -> tuple[dict[str, str], Optional[str]]:
    """GUID card URL (http://) → public redirect Location → fetch building page with cookies."""
    try:
        session = curl_requests.Session()
        # Шаг 1: получаем Location без следования редиректу (http:// работает без авторизации)
        res1 = session.get(
            f"http://domclick.ru/card/info__building__{geo_guid}",
            headers=_SUGGEST_HEADERS,
            timeout=8,
            impersonate="chrome110",
            allow_redirects=False,
        )
        location = res1.headers.get("Location") or res1.headers.get("location") or ""
        if not location:
            # Если сервер вернул 200 с JS-редиректом — пробуем из тела
            m_body = re.search(r'https?://([^"\']+\.domclick\.ru/building/[^"\'#?]+)', res1.text)
            location = m_body.group(0) if m_body else ""
        if not location:
            logging.debug("Domclick GUID: no Location (status=%s)", res1.status_code)
            return {}, None
        # Нормализуем URL
        if location.startswith("/"):
            location = f"https://domclick.ru{location}"
        m = re.match(r"https?://([^.]+)\.domclick\.ru/building/([^#?/]+(?:/[^#?/]+)*)", location)
        if not m:
            logging.debug("Domclick GUID: Location not a building URL: %s", location)
            return {}, None
        subdomain, slug = m.group(1), m.group(2)
        building_url = f"https://{subdomain}.domclick.ru/building/{slug}"
        # Шаг 2: запрашиваем страницу здания с куками
        headers2 = dict(_DOMCLICK_HEADERS)
        cookie = _combined_cookie()
        if cookie:
            headers2["Cookie"] = cookie
        res2 = session.get(building_url, headers=headers2, timeout=12, impersonate="chrome110")
        if res2.status_code != 200 or "__qrator" in res2.text:
            logging.debug("Domclick GUID: page blocked (status=%s)", res2.status_code)
            return {}, building_url
        parsed = _extract_fields_from_html(res2.text)
        return parsed, building_url
    except Exception as exc:
        logging.debug("Domclick GUID: %s", exc)
    return {}, None


def _get_building_from_user_realty(geo_guid: str) -> dict[str, str]:
    """Ищет данные о здании по geo_guid через /my-home/api/v3/user_realty (требует CAS-куки)."""
    auth = _load_mobile_auth()
    cookie = auth.get("cookie")
    if not cookie or not geo_guid:
        return {}
    headers = {
        "Host": "api.domclick.ru",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru",
        "Origin": "https://domclick.ru",
        "Referer": "https://domclick.ru/",
        "User-Agent": "iOS; 26.3; Apple; unrecognized; 9.30.0; 3; 7F06BEFC-9EC3-45A3-B554-D2FE00C9958A; CUSTOMER",
        "Cookie": cookie,
    }
    try:
        session = curl_requests.Session()
        r = session.get(
            _USER_REALTY_URL,
            params={"offset": "0", "limit": "100", "order": "created_dt"},
            headers=headers,
            timeout=10,
            impersonate="chrome110",
        )
        if r.status_code != 200:
            return {}
        estates = (r.json().get("result") or {}).get("realty_estates", [])
        fields: dict[str, str] = {}
        for estate in estates:
            if estate.get("geo_guid") != geo_guid:
                continue
            bld = estate.get("building") or {}
            if bld.get("build_date"):
                year = bld["build_date"][:4]
                if YEAR_VALUE_RE.search(year):
                    _set_field(fields, "build_year", year)
            if bld.get("floors_total"):
                _set_field(fields, "floors", str(bld["floors_total"]))
            if bld.get("building_series"):
                _set_field(fields, "building_series", str(bld["building_series"]))
            if fields:
                break
        return fields
    except Exception as exc:
        logging.debug("user_realty API: %s", exc)
        return {}


def _extra_slugs_from_canonical(
    canonical: str,
    district_slug: Optional[str],
    street_slug: str,
    house_slug: str,
) -> list[str]:
    """Из canonical-адреса suggest извлекаем микрорайон → дополнительные slug-кандидаты."""
    extras: list[str] = []
    for part in canonical.split(","):
        part = part.strip()
        if any(m in part.lower() for m in ("м-н", "мкр", "микрорайон")):
            clean = re.sub(r"\s*(м-н|мкр|микрорайон)\s*$", "", part, flags=re.IGNORECASE).strip()
            micro = MICRODISTRICT_SLUGS.get(clean.lower()) or _slugify(part)
            if district_slug:
                extras.append(f"{district_slug}--{micro}--{street_slug}--{house_slug}")
            extras.append(f"{micro}--{street_slug}--{house_slug}")
            break
    return extras


def get_building_from_domclick(
    cadastral_number: str,
    city: Optional[str],
    street: Optional[str],
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
    city_district: Optional[str] = None,
    dadata_addr: Optional[str] = None,
    region: Optional[str] = None,
    region_type: Optional[str] = None,
    area: Optional[str] = None,
    area_type: Optional[str] = None,
    settlement_type: Optional[str] = None,
    street_type: Optional[str] = None,
) -> tuple[dict[str, str], Optional[str]]:
    """Suggest → slug candidates → HTML-страница → поля. Возвращает (поля, url)."""
    house_num, block_num = normalize_house_and_block(house, block)
    if not street or not house_num:
        return {}, None

    subdomain = _city_subdomain(city, settlement)
    cad_key = cadastral_number if cadastral_number != "Не указан" else None
    known = _known_building(cad_key)
    merged: dict[str, str] = dict(known.get("fields") or {}) if known else {}
    best_url: Optional[str] = None
    if known and known.get("slug"):
        best_url = f"https://{subdomain}.domclick.ru/building/{known['slug']}"

    # Suggest: подтверждаем наличие здания в Domclick + canonical-адрес для лучших slug
    # Для малых городов используем полный адрес из Dadata (с регионом) — иначе suggest не найдёт
    place = (city or settlement or "").strip()
    house_str = f"{house_num}/{block_num}" if block_num else house_num
    short_query = f"{place}, {street}, {house_str}"
    geo_guid, canonical, suggest_url = _suggest_building(dadata_addr or short_query)
    if not geo_guid and dadata_addr:
        geo_guid, canonical, suggest_url = _suggest_building(short_query)

    # GUID card redirect → полные данные со страницы здания (Qrator cookies)
    if geo_guid:
        guid_fields, guid_url = _get_building_via_guid(geo_guid)
        if guid_fields:
            merged = _merge_fields(merged, guid_fields)
            return merged, guid_url or best_url

    # Fallback: user_realty API (CAS-куки, без Qrator, но только частичные поля)
    if geo_guid:
        ur_fields = _get_building_from_user_realty(geo_guid)
        if ur_fields:
            merged = _merge_fields(merged, ur_fields)
            if merged:
                return merged, best_url

    # Fallback: известный slug из KNOWN_BUILDINGS
    if not geo_guid and not known:
        logging.debug("Domclick: здание не найдено через suggest, пропускаем HTML")
        return merged, best_url

    for slug in _slug_candidates(city, settlement, street, house_num, block_num, city_district, cad_key):
        html = _fetch_building_page(curl_requests.Session(), subdomain, slug)
        if not html:
            continue
        parsed = _extract_fields_from_html(html)
        if parsed:
            merged = _merge_fields(merged, parsed)
            best_url = f"https://{subdomain}.domclick.ru/building/{slug}"

    if merged:
        return merged, best_url
    return {}, None


def _make_bbox(lat: float, lon: float, delta: float = 0.0002) -> tuple[str, str]:
    """Tiny bounding box (~22m x ~13m at 55°N) around a point."""
    sw = f"{lat - delta:.6f},{lon - delta:.6f}"
    ne = f"{lat + delta:.6f},{lon + delta:.6f}"
    return sw, ne


def _building_url_from_seo(data: dict) -> Optional[str]:
    try:
        parts = (
            data.get("result", {})
            .get("items", [{}])[0]
            .get("seo_info", {})
            .get("display_name_parts", [])
        )
        for part in parts:
            if part.get("is_building") and part.get("seo_uri"):
                subdomain = part.get("subdomain", "ufa")
                return f"https://{subdomain}.domclick.ru{part['seo_uri']}"
    except Exception:
        pass
    return None


def get_building_from_domclick_api(
    lat: float,
    lon: float,
    house: Optional[str] = None,
    block: Optional[str] = None,
) -> tuple[dict[str, str], Optional[str]]:
    """Публичный мобильный JSON API Domclick по координатам. Возвращает (поля, url)."""
    sw, ne = _make_bbox(lat, lon)
    params = [
        ("category", "living"),
        ("deal_type", "sale"),
        ("enable_mixed_ranking", "1"),
        ("include_realty_meta", "1"),
        ("ne", ne),
        ("offer_type", "flat"),
        ("offer_type", "layout"),
        ("offset", "0"),
        ("sale_price_full", "1"),
        ("sort", "qi"),
        ("sort_dir", "desc"),
        ("sw", sw),
        ("zoom", "18"),
    ]
    headers = {
        "Host": "bff-search-mobile.domclick.ru",
        "X-Service": "mobile/domclick_ios/9.30.0",
        "Accept": "*/*",
        "Accept-Language": "ru",
        "User-Agent": (
            "iOS; 26.3; Apple; unrecognized; 9.30.0; 3; "
            "7F06BEFC-9EC3-45A3-B554-D2FE00C9958A; CUSTOMER"
        ),
        "x-user-role": "CUSTOMER",
    }

    try:
        session = curl_requests.Session()
        res = session.get(
            _MOBILE_API_URL, params=params, headers=headers, timeout=12, impersonate="chrome110"
        )
        if res.status_code != 200:
            logging.warning("Domclick mobile API: HTTP %s", res.status_code)
            return {}, None

        data = res.json()
        if not data.get("success"):
            return {}, None

        realty_meta = (data.get("result") or {}).get("realty_meta") or {}
        house_meta = realty_meta.get("house", {})

        fields: dict[str, str] = {}
        if house_meta.get("build_year"):
            fields["build_year"] = str(house_meta["build_year"])
        if house_meta.get("floors"):
            fields["floors"] = str(house_meta["floors"])
        if house_meta.get("wall_type"):
            fields["wall_material"] = _WALL_TYPE_MAP.get(
                house_meta["wall_type"], house_meta["wall_type"].capitalize()
            )

        # Дополнительные поля из полного JSON (если API когда-нибудь вернёт больше)
        _fields_from_json(data, fields)

        building_url = _building_url_from_seo(data)

        # Validate URL matches the requested house+block to avoid wrong-building matches
        if building_url and house:
            h_num, b_num = normalize_house_and_block(house, block)
            expected_suffix = f"--{_house_slug_part(h_num, b_num)}"
            if expected_suffix not in building_url:
                logging.debug("Domclick mobile API: URL %s doesn't match house %s, discarding", building_url, expected_suffix)
                return {}, None

        return fields, building_url

    except Exception as exc:
        logging.warning("Domclick mobile API error: %s", exc)
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
