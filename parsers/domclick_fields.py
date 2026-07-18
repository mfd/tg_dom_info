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
    "теплоснабжение": "heat_supply",
    "энергоснабжение": "power_supply",
    "вентиляция": "ventilation",
    "тип перекрытий": "ceiling_type",
    "тип фундамента": "foundation_type",
    "класс энергоэффективности": "energy_class",
    "газоснабжение": "gas_supply",
}

FIELD_DISPLAY_NAMES: dict[str, str] = {
    "build_year": "Год постройки",
    "wall_material": "Материал стен",
    "building_series": "Серия дома",
    "floors": "Количество этажей",
    "apartments": "Количество квартир",
    "garbage_chute": "Мусоропровод",
    "playground": "Детская площадка",
    "entrances": "Количество подъездов",
    "elevators": "Количество лифтов",
    "cold_water": "Холодное водоснабжение",
    "hot_water": "Горячее водоснабжение",
    "sewage": "Водоотведение",
    "heat_supply": "Теплоснабжение",
    "power_supply": "Энергоснабжение",
    "ventilation": "Вентиляция",
    "ceiling_type": "Тип перекрытий",
    "foundation_type": "Тип фундамента",
    "energy_class": "Класс энергоэффективности",
    "gas_supply": "Газоснабжение",
}

BUILDING_FIELD_ORDER: tuple[str, ...] = (
    "build_year",
    "wall_material",
    "building_series",
    "floors",
    "apartments",
    "garbage_chute",
    "playground",
    "entrances",
    "elevators",
    "cold_water",
    "hot_water",
    "sewage",
    "heat_supply",
    "power_supply",
    "ventilation",
    "ceiling_type",
    "foundation_type",
    "energy_class",
    "gas_supply",
)

# Подписи / ключи JSON с годом постройки
YEAR_JSON_KEYS: frozenset[str] = frozenset(
    {
        # "buildyear" убран — это ключ из объявлений (house.buildYear), а не карточки здания
        "yearbuilt",
        "builtyear",
        "constructionyear",
        "build_year",
        "year_built",
    }
)

# JSON-ключи Domclick → код поля (web + mobile API)
JSON_FIELD_KEYS: dict[str, str] = {
    # build year (только builtyear — buildyear это ключ в объявлениях, не в карточке здания)
    "yearbuilt": "build_year",
    "builtyear": "build_year",
    "constructionyear": "build_year",
    "year": "build_year",
    # wall material
    "wallmaterial": "wall_material",
    "materialwalls": "wall_material",
    "housematerial": "wall_material",
    "material": "wall_material",
    # building series
    "buildingseries": "building_series",
    "series": "building_series",
    "projecttype": "building_series",
    # floors
    "floorscount": "floors",
    "floorstotal": "floors",
    "floors": "floors",
    "floorsnum": "floors",
    # apartments
    "flatscount": "apartments",
    "flats": "apartments",
    "apartmentscount": "apartments",
    # apartments count
    "flats": "apartments",
    # entrances / elevators
    "entrancescount": "entrances",
    "entrancecount": "entrances",    # entranceCount (Domclick building obj)
    "porchescount": "entrances",
    "elevatorscount": "elevators",
    # garbage chute
    "chute": "garbage_chute",
    "garbagechute": "garbage_chute",
    # playground
    "playground": "playground",
    # utilities (Domclick uses *Type suffix)
    "heatsupply": "heat_supply",
    "heatingtype": "heat_supply",    # heatingType
    "powersupply": "power_supply",
    "electricitysupply": "power_supply",
    "electricaltype": "power_supply",  # electricalType
    "ventilation": "ventilation",
    "ventilationtype": "ventilation",  # ventilationType
    "gassupply": "gas_supply",
    "coldwatertype": "cold_water",   # coldWaterType
    "coldwater": "cold_water",
    "hotwatertype": "hot_water",     # hotWaterType
    "hotwater": "hot_water",
    "seweragetype": "sewage",        # sewerageType
    "sewage": "sewage",
    "sewagesystem": "sewage",
    # structural
    "ceilingtype": "ceiling_type",
    "overlapping": "ceiling_type",
    "floortype": "ceiling_type",     # floorType (Domclick: тип перекрытий)
    "foundationtype": "foundation_type",
    "foundation": "foundation_type",
    "energyclass": "energy_class",
    "energyefficiency": "energy_class",
}

YEAR_PAGE_TEXT_RE: Pattern[str] = re.compile(
    r"Год\s+постройки[^0-9]{0,40}(\d{4})",
    re.IGNORECASE,
)

YEAR_VALUE_RE: Pattern[str] = re.compile(r"\b(19\d{2}|20\d{2})\b")

CITY_SUBDOMAINS: dict[str, str] = {
    # Только города, где _slugify() даёт неверный субдомен Domclick
    "москва": "msk",
    "санкт-петербург": "spb",
    "нижний новгород": "nn",
    "ростов-на-дону": "rostov",
}

DISTRICT_SLUGS: dict[str, str] = {}

MICRODISTRICT_SLUGS: dict[str, str] = {
    # щ → Domclick транслитерирует как "sh" (не стандартное "sch")
    "зеленая роща": "zelenaya-rosha-m-n",
    "зелёная роща": "zelenaya-rosha-m-n",
}

STREET_SLUG_ALIASES: dict[str, str] = {}

KNOWN_BUILDINGS: dict[str, dict] = {}


def normalize_field_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
