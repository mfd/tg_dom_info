"""Поиск характеристик дома на reformagkh.ru."""

import re
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
import urllib3

from utils.house import normalize_house_and_block, normalize_house_token

# Отключаем предупреждения об отключенном SSL для корректной работы с гос. сайтами
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_building_from_reformagkh(
    city: Optional[str],
    street: str,
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
) -> Tuple[dict, Optional[str]]:
    """Поиск характеристик дома на reformagkh.ru. Возвращает (поля, url)."""
    house_num, block_num = normalize_house_and_block(house, block)
    place = (city or settlement or "").strip()
    if not place or not street or not house_num:
        return {}, None

    house_str = f"{normalize_house_token(house_num)}/{block_num}" if block_num else normalize_house_token(house_num)
    query = f"{place} {street} {house_str}"

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})

    try:
        res = session.get(
            "https://www.reformagkh.ru/search/houses",
            params={"query": query},
            timeout=8, verify=False,
        )
        if res.status_code != 200:
            return {}, None
        soup = BeautifulSoup(res.text, "html.parser")
        link = soup.find("a", href=re.compile(r"/myhouse/profile/passport/\d+"))
        if not link:
            return {}, None
        house_url = f"https://www.reformagkh.ru{link['href']}"
    except Exception:
        return {}, None

    try:
        res2 = session.get(house_url, timeout=8, verify=False)
        if res2.status_code != 200:
            return {}, None
        soup2 = BeautifulSoup(res2.text, "html.parser")
        fields: dict = {}
        for tr in soup2.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True).lower()
            value = cells[-1].get_text(strip=True)
            if not value:
                continue
            if "год постройки" in label or "год ввода" in label:
                m = re.search(r"\b(19|20)\d{2}\b", value)
                if m and not fields.get("build_year"):
                    fields["build_year"] = m.group(0)
            elif "материал несущих стен" in label:
                if not fields.get("wall_material"):
                    fields["wall_material"] = value.capitalize()
            elif "количество этажей" in label:
                m = re.search(r"\d+", value)
                if m and not fields.get("floors"):
                    fields["floors"] = m.group(0)
        return fields, house_url if fields else None
    except Exception:
        return {}, None
