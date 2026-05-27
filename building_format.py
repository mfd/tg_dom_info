"""Форматирование характеристик здания для консоли и Telegram."""

from typing import Optional

from domclick_parse_dict import BUILDING_FIELD_ORDER, FIELD_DISPLAY_NAMES


def format_building_fields(info: dict, source_url: Optional[str] = None) -> str:
    lines = []
    for key in BUILDING_FIELD_ORDER:
        value = info.get(key)
        if not value:
            continue
        label = FIELD_DISPLAY_NAMES.get(key, key)
        lines.append(f"{label}: {value}")
    if source_url:
        lines.append(f"Источник: {source_url}")
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
    if mingkh_url:
        msg += f"\n🔗 [МинЖКХ]({mingkh_url})"
    if domclick_url and domclick_url != mingkh_url:
        msg += f"\n🔗 [Domclick]({domclick_url})"
    elif domclick_url:
        msg += f"\n🔗 [Domclick]({domclick_url})"
    if gis_url:
        msg += f"\n🔗 [ГИС ЖКХ]({gis_url})"
    return msg
