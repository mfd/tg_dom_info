"""Парсинг МинЖКХ: словари и функции скрапинга."""

import re
from typing import FrozenSet, Optional, Pattern

import requests
from bs4 import BeautifulSoup
import urllib3

from utils.house import (
    house_regex_fragment,
    normalize_house_and_block,
    normalize_house_token,
)

# Отключаем предупреждения об отключенном SSL для корректной работы с гос. сайтами
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Константы (из mingkh_parse_dict.py) ---

YEAR_DT_LABELS: dict[str, str] = {
    "год постройки": "build_year",
    "год ввода в эксплуатацию": "commissioning_year",
}

YEAR_DT_LABELS_ORDER: tuple[str, ...] = tuple(YEAR_DT_LABELS.keys())

YEAR_TEXT_REGEX_PARTS: tuple[str, ...] = (
    "постройки",
    r"ввода\s+в\s+эксплуатацию",
)

YEAR_PAGE_TEXT_RE: Pattern[str] = re.compile(
    rf"Год\s+(?:{'|'.join(YEAR_TEXT_REGEX_PARTS)})\s*[:\s]*(\d{{4}})",
    re.IGNORECASE,
)

YEAR_VALUE_RE: Pattern[str] = re.compile(r"\d{4}")


def normalize_label(text: str) -> str:
    return text.strip().lower()


# --- Функции скрапинга (из parser_utils.py) ---

def _row_matches_house(row_text: str, house_num: str, block_num: Optional[str]) -> bool:
    """Сопоставление адреса в строке таблицы без ложных срабатываний на площади (3847.5 → 38)."""
    text = row_text.lower()
    h = house_regex_fragment(house_num)
    if block_num:
        b = re.escape(block_num)
        patterns = (
            rf',\s*{h}\s*корпус\s*{b}\b',
            rf',\s*{h}\s*к\s*{b}\b',
            rf',\s*{h}/{b}\b',
            rf'\b{h}/{b}\b',
        )
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    m = re.search(rf',\s*({h})(?:\s|$)', text, re.IGNORECASE)
    if not m:
        return False
    if normalize_house_token(m.group(1).replace(" ", "")) != normalize_house_token(house_num):
        return False
    rest = text[m.end():]
    return not re.match(r'\s*(?:/|корпус|к\s*\d)', rest)


def _extract_year_from_soup(soup: BeautifulSoup) -> Optional[str]:
    """Год постройки или ввода в эксплуатацию из карточки дома."""
    years_by_label: dict[str, str] = {}
    for dl in soup.find_all("dl", class_=lambda c: c and "dl-horizontal" in c):
        for dt in dl.find_all("dt"):
            label = normalize_label(dt.get_text())
            if label not in YEAR_DT_LABELS_ORDER:
                continue
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            match = YEAR_VALUE_RE.search(dd.get_text(strip=True))
            if match:
                years_by_label[label] = match.group(0)
    for label in YEAR_DT_LABELS_ORDER:
        if label in years_by_label:
            return years_by_label[label]
    page_match = YEAR_PAGE_TEXT_RE.search(soup.get_text())
    return page_match.group(1) if page_match else None


def _parse_mingkh_html(session, url):
    """Парсинг карточки дома."""
    try:
        res = session.get(url, timeout=5, verify=False)
        if "не робот" in res.text:
            return None, None, None
        soup = BeautifulSoup(res.text, "html.parser")
        build_year = _extract_year_from_soup(soup)

        wall_material = None
        for dl in soup.find_all("dl", class_=lambda c: c and "dl-horizontal" in c):
            for dt in dl.find_all("dt"):
                if "стены" not in dt.get_text(strip=True).lower():
                    continue
                dd = dt.find_next_sibling("dd")
                if dd:
                    wall_material = dd.get_text(strip=True).capitalize()
                    break
        return build_year, wall_material, url
    except Exception:
        return None, None, None


def get_year_from_mingkh_smart(
    cadastral_number: str,
    city: str,
    street: str,
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
):
    """Шаг 2: Умный поиск на МинЖКХ со строгой фильтрацией по дому и корпусу."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://dom.mingkh.ru/"})

    house_num, block_num = normalize_house_and_block(house, block)
    place = (city or settlement or "").strip()

    # Поиск по тексту с фильтрацией строк
    if place and street and house_num:
        street_words = street.lower().split()
        ignored = ["степана", "ул", "улица", "проспект", "пр", "академика", "генерала", "летчика", "маршала"]
        filtered = [w for w in street_words if w not in ignored]
        core_street = filtered[0] if filtered else street

        house_query = (
            f"{normalize_house_token(house_num)}/{block_num}"
            if block_num
            else normalize_house_token(house_num)
        )
        query_parts = [place.lower(), core_street, house_query]
        query_str = " ".join(query_parts)
        url = f"https://dom.mingkh.ru/search/?address={query_str}&searchtype=house"
        try:
            res = session.get(url, timeout=5, verify=False)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                table = soup.find('table', class_='table')
                if table:
                    for row in table.find_all('tr'):
                        row_text = row.get_text()
                        if not _row_matches_house(row_text, house_num, block_num):
                            continue
                        a_tag = row.find('a', href=True)
                        if a_tag and "/streets/" not in a_tag['href']:
                            return _parse_mingkh_html(session, f"https://dom.mingkh.ru{a_tag['href']}")
        except Exception:
            pass
    return None, None, None
