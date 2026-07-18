"""Агрегатор источников данных о здании: Domclick → МинЖКХ → РеформаЖКХ."""

from typing import Optional, Tuple

from parsers.domclick import get_building_from_domclick, get_building_from_domclick_api
from parsers.mingkh import get_year_from_mingkh_smart
from parsers.reformagkh import get_building_from_reformagkh
from utils.house import normalize_house_and_block, normalize_house_token


def get_building_info(
    cadastral_number: str,
    city: Optional[str],
    street: str,
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
    city_district: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    dadata_addr: Optional[str] = None,
    region: Optional[str] = None,
    region_type: Optional[str] = None,
    area: Optional[str] = None,
    area_type: Optional[str] = None,
    settlement_type: Optional[str] = None,
    street_type: Optional[str] = None,
) -> Tuple[dict, Optional[str], Optional[str]]:
    """Fallback-цепочка: HTML Domclick → mobile API (fallback) → МинЖКХ → РеформаЖКХ.
    Возвращает (поля, url_минжкх, url_domclick)."""
    # 1. Domclick: suggest → GUID redirect → HTML → полные поля здания (требует свежих кук)
    dc_fields, domclick_url = get_building_from_domclick(
        cadastral_number, city, street, house, block, settlement, city_district,
        dadata_addr=dadata_addr,
        region=region, region_type=region_type,
        area=area, area_type=area_type,
        settlement_type=settlement_type, street_type=street_type,
    )
    # 2. Domclick mobile API по координатам — fallback когда HTML заблокирован Qrator
    if not dc_fields and lat and lon:
        dc_fields, mobile_url = get_building_from_domclick_api(lat, lon, house=house, block=block)
        if dc_fields:
            domclick_url = mobile_url or domclick_url

    # Если Domclick вернул полные данные (есть год постройки) — возвращаем сразу
    if dc_fields and dc_fields.get("build_year"):
        return dc_fields, None, domclick_url

    # 3. МинЖКХ
    year, material, mingkh_url = get_year_from_mingkh_smart(
        cadastral_number, city, street, house, block, settlement
    )
    mingkh_fields: dict = {}
    if year:
        mingkh_fields["build_year"] = year
    if material:
        mingkh_fields["wall_material"] = material

    # 4. Реформа ЖКХ (reformagkh.ru)
    rgkh_fields, rgkh_url = get_building_from_reformagkh(city, street, house, block, settlement)

    # Мержим: Domclick + МинЖКХ + Реформа (приоритет в таком порядке)
    merged = {}
    for source in (rgkh_fields, mingkh_fields, dc_fields):
        for k, v in (source or {}).items():
            if v and k not in merged:
                merged[k] = v

    best_mingkh_url = mingkh_url or rgkh_url
    return merged, best_mingkh_url, domclick_url


def get_building_year(
    cadastral_number: str,
    city: Optional[str],
    street: str,
    house: str,
    block: Optional[str] = None,
    settlement: Optional[str] = None,
    city_district: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Совместимость: (год, материал, url)."""
    info, mingkh_url, domclick_url = get_building_info(
        cadastral_number, city, street, house, block, settlement, city_district,
    )
    url = mingkh_url or domclick_url
    return info.get("build_year"), info.get("wall_material"), url
