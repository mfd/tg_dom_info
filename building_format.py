"""Форматирование характеристик здания для консоли и Telegram."""

from typing import Optional

from domclick_parse_dict import BUILDING_FIELD_ORDER, FIELD_DISPLAY_NAMES


def format_building_fields(
    info: dict,
    mingkh_url: Optional[str] = None,
    domclick_url: Optional[str] = None,
) -> str:
    lines = []
    for key in BUILDING_FIELD_ORDER:
        value = info.get(key)
        if not value:
            continue
        label = FIELD_DISPLAY_NAMES.get(key, key)
        lines.append(f"{label}: {value}")
    if mingkh_url:
        lines.append(f"МинЖКХ: {mingkh_url}")
    if domclick_url:
        lines.append(f"Domclick: {domclick_url}")
    return "\n".join(lines)


def format_building_telegram(
    info: dict,
    mingkh_url: Optional[str] = None,
    domclick_url: Optional[str] = None,
    gis_url: Optional[str] = None,
) -> str:
    msg = ""
    if info.get("build_year"):
        msg += f"📅 **Год постройки:** `{info['build_year']}`\n"
    for key in BUILDING_FIELD_ORDER:
        if key == "build_year":
            continue
        value = info.get(key)
        if not value:
            continue
        label = FIELD_DISPLAY_NAMES.get(key, key)
        msg += f"📋 **{label}:** `{value}`\n"
    links = []
    if mingkh_url:
        links.append(f"🔗 [МинЖКХ]({mingkh_url})")
    if domclick_url:
        links.append(f"🔗 [Domclick]({domclick_url})")
    if gis_url:
        links.append(f"🔗 [ГИС ЖКХ]({gis_url})")
    if links:
        msg += "\n" + "\n".join(links)
    return msg
