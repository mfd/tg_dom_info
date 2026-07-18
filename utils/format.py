"""Форматирование характеристик здания для консоли и Telegram (HTML)."""

from typing import Optional

from parsers.domclick_fields import BUILDING_FIELD_ORDER, FIELD_DISPLAY_NAMES

_SPOILER_FROM = "cold_water"  # всё начиная с холодного водоснабжения — в блок


def _e(text: str) -> str:
    """Экранирование HTML-спецсимволов."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    main_lines = []
    spoiler_lines = []
    in_spoiler = False

    if info.get("build_year"):
        main_lines.append(f"<b>Год постройки:</b> <code>{_e(info['build_year'])}</code>")

    for key in BUILDING_FIELD_ORDER:
        if key == "build_year":
            continue
        if key == _SPOILER_FROM:
            in_spoiler = True
        value = info.get(key)
        if not value:
            continue
        label = FIELD_DISPLAY_NAMES.get(key, key)
        if in_spoiler:
            spoiler_lines.append(f"<b>{_e(label)}:</b> {_e(value)}")
        else:
            main_lines.append(f"<b>{_e(label)}:</b> <code>{_e(value)}</code>")

    msg = "\n".join(main_lines)
    if msg:
        msg += "\n"

    if spoiler_lines:
        msg += "<blockquote expandable>" + "\n".join(spoiler_lines) + "</blockquote>\n"

    links = []
    if mingkh_url:
        label = "Реформа ЖКХ" if "reformagkh" in mingkh_url else "МинЖКХ"
        links.append(f'<a href="{mingkh_url}">{label}</a>')
    if domclick_url:
        links.append(f'<a href="{domclick_url}">Domclick</a>')
    if gis_url:
        links.append(f'<a href="{gis_url}">ГИС ЖКХ</a>')
    if links:
        msg += "\n" + " | ".join(links)
    return msg
