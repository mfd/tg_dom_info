"""Нормализация номера дома и корпуса."""

import re
from typing import Optional, Tuple

_HOUSE_LETTER_MAP = str.maketrans("abvgdezijklmnoprstufhy", "абвгдезийклмнопрстуфху")


def normalize_house_and_block(house: str, block: Optional[str] = None) -> Tuple[str, Optional[str]]:
    house = (house or "").strip()
    block = (block or "").strip() or None
    if "/" in house:
        parts = house.split("/", 1)
        return parts[0].strip(), (parts[1].strip() or block)
    if block:
        return house, block
    return house, None


def normalize_house_token(house: str) -> str:
    return house.strip().lower().translate(_HOUSE_LETTER_MAP)


def house_regex_fragment(house_num: str) -> str:
    match = re.match(r"^(\d+)([a-zа-яё]?)$", house_num.strip(), re.IGNORECASE)
    if not match:
        return re.escape(normalize_house_token(house_num))
    digits, letter = match.group(1), match.group(2)
    if not letter:
        return re.escape(digits)
    letter = letter.lower().translate(_HOUSE_LETTER_MAP)
    return rf"{re.escape(digits)}\s*[{re.escape(letter)}{letter.upper()}]"
