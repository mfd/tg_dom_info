"""Словарь подписей полей МинЖКХ для парсинга года постройки / ввода в эксплуатацию."""

import re
from typing import FrozenSet, Pattern

# Подписи <dt> на карточке дома (ключ — нормализованный текст, значение — код поля)
YEAR_DT_LABELS: dict[str, str] = {
    "год постройки": "build_year",
    "год ввода в эксплуатацию": "commissioning_year",
}

# Порядок приоритета при нескольких полях на странице
YEAR_DT_LABELS_ORDER: tuple[str, ...] = tuple(YEAR_DT_LABELS.keys())

# Фрагменты для fallback-regex по тексту всей страницы
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


def is_year_dt_label(label: str) -> bool:
    return normalize_label(label) in YEAR_DT_LABELS


def year_label_codes() -> FrozenSet[str]:
    return frozenset(YEAR_DT_LABELS.values())
