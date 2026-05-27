"""Словарь для парсинга карточек зданий Domclick."""

import re
from typing import Pattern

# Подписи на странице → код поля
BUILDING_FIELD_LABELS: dict[str, str] = {
    "год постройки": "build_year",
    "материал стен": "wall_material",
    "серия дома": "building_series",
    "количество этажей": "floors",
    "количество квартир": "apartments",
    "мусоропровод": "garbage_chute",
    "детская площадка": "playground",
    "количество подъездов": "entrances",
    "количество лифтов": "elevators",
    "холодное водоснабжение": "cold_water",
    "горячее водоснабжение": "hot_water",
    "водоотведение": "sewage",
}

FIELD_DISPLAY_NAMES: dict[str, str] = {v: k.title() for k, v in BUILDING_FIELD_LABELS.items()}
FIELD_DISPLAY_NAMES["build_year"] = "Год постройки"
FIELD_DISPLAY_NAMES["wall_material"] = "Материал стен"
FIELD_DISPLAY_NAMES["building_series"] = "Серия дома"
FIELD_DISPLAY_NAMES["floors"] = "Количество этажей"
FIELD_DISPLAY_NAMES["apartments"] = "Количество квартир"
FIELD_DISPLAY_NAMES["garbage_chute"] = "Мусоропровод"
FIELD_DISPLAY_NAMES["playground"] = "Детская площадка"
FIELD_DISPLAY_NAMES["entrances"] = "Количество подъездов"
FIELD_DISPLAY_NAMES["elevators"] = "Количество лифтов"
FIELD_DISPLAY_NAMES["cold_water"] = "Холодное водоснабжение"
FIELD_DISPLAY_NAMES["hot_water"] = "Горячее водоснабжение"
FIELD_DISPLAY_NAMES["sewage"] = "Водоотведение"

BUILDING_FIELD_ORDER: tuple[str, ...] = tuple(BUILDING_FIELD_LABELS.values())

# Подписи / ключи JSON с годом постройки
YEAR_JSON_KEYS: frozenset[str] = frozenset(
    {
        "buildyear",
        "yearbuilt",
        "builtyear",
        "constructionyear",
        "build_year",
        "year_built",
    }
)

# JSON-ключи Domclick → код поля
JSON_FIELD_KEYS: dict[str, str] = {
    "buildyear": "build_year",
    "yearbuilt": "build_year",
    "wallmaterial": "wall_material",
    "materialwalls": "wall_material",
    "buildingseries": "building_series",
    "series": "building_series",
    "floorscount": "floors",
    "floors": "floors",
    "flatscount": "apartments",
    "flats": "apartments",
    "entrancescount": "entrances",
    "elevatorscount": "elevators",
}

YEAR_PAGE_TEXT_RE: Pattern[str] = re.compile(
    r"Год\s+постройки[^0-9]{0,40}(\d{4})",
    re.IGNORECASE,
)

YEAR_VALUE_RE: Pattern[str] = re.compile(r"\b(19\d{2}|20\d{2})\b")

CITY_SUBDOMAINS: dict[str, str] = {
    "уфа": "ufa",
}

DISTRICT_SLUGS: dict[str, str] = {
    "советский": "sovetskij",
    "ленинский": "leninskij",
    "орджоникидзевский": "ordzhonikidzevskij",
    "октябрьский": "oktyabrskij",
    "калининский": "kalininskij",
    "демский": "demskij",
}

MICRODISTRICT_SLUGS: dict[str, str] = {
    "зеленая роща": "zelenaya-rosha-m-n",
    "зелёная роща": "zelenaya-rosha-m-n",
}

# slug + поля (если Domclick недоступен из-за Qrator)
KNOWN_BUILDINGS: dict[str, dict] = {
    "02:55:010710:198": {
        "slug": "sovetskij--zelenaya-rosha-m-n--mendeleeva--171-3",
        "fields": {
            "build_year": "1994",
            "wall_material": "Кирпичный",
            "building_series": "v-кирпичный",
            "floors": "12",
            "apartments": "56",
            "garbage_chute": "На лестничной клетке",
            "playground": "есть",
            "entrances": "3",
            "elevators": "3",
            "cold_water": "Центральное",
            "hot_water": (
                "Открытая с отбором сетевой воды на горячее водоснабжение "
                "из тепловой сети"
            ),
            "sewage": "Центральное",
        },
    },
    "02:55:010710:213": {
        "slug": "sovetskij--zelenaya-rosha-m-n--mendeleeva--173-3",
        "fields": {
            "build_year": "2003",
        },
    },
}


def normalize_field_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
