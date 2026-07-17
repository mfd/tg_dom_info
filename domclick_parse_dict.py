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
        "buildyear",
        "yearbuilt",
        "builtyear",
        "constructionyear",
        "build_year",
        "year_built",
    }
)

# JSON-ключи Domclick → код поля (web + mobile API)
JSON_FIELD_KEYS: dict[str, str] = {
    # build year
    "buildyear": "build_year",
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
    # entrances / elevators
    "entrancescount": "entrances",
    "porchescount": "entrances",
    "elevatorscount": "elevators",
    # utilities
    "heatsupply": "heat_supply",
    "powersupply": "power_supply",
    "electricitysupply": "power_supply",
    "ventilation": "ventilation",
    "gassupply": "gas_supply",
    # structural
    "ceilingtype": "ceiling_type",
    "overlapping": "ceiling_type",
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
    "черемушки": "cheryomushki",
    "черёмушки": "cheryomushki",
}

# Улица (нормализованное имя) → slug на Domclick (без «ул» внутри названия)
STREET_SLUG_ALIASES: dict[str, str] = {
    "минигали губайдуллина": "minigali-gubajdullina",
    "менделеева": "mendeleeva",
    "степана злобина": "stepana-zlobina",
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
            "heat_supply": "Центральное",
            "power_supply": "Центральное",
            "ventilation": "Приточно-вытяжная",
            "ceiling_type": "Железобетонный",
            "foundation_type": "Ленточный",
            "energy_class": "Не присвоен",
            "gas_supply": "Центральное",
        },
    },
    "02:55:010710:213": {
        "slug": "sovetskij--zelenaya-rosha-m-n--mendeleeva--173-3",
        "fields": {
            "build_year": "2003",
        },
    },
    "02:55:010701:2416": {
        "slug": "ulica-minigali-gubajdullina--10-1",
        "fields": {
            "build_year": "2023",
            "wall_material": "Кирпичный",
            "floors": "27",
            "entrances": "2",
        },
    },
}


def normalize_field_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
