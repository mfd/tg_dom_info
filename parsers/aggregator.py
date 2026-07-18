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
    if dc_fields:
        return dc_fields, None, domclick_url

    # 2. Domclick mobile API по координатам — fallback когда HTML заблокирован Qrator
    if lat and lon:
        dc_fields, mobile_url = get_building_from_domclick_api(lat, lon, house=house, block=block)
        if dc_fields:
            return dc_fields, None, mobile_url or domclick_url

    # 3. МинЖКХ
    info: dict = {}
    year, material, mingkh_url = get_year_from_mingkh_smart(
        cadastral_number, city, street, house, block, settlement
    )
    if year:
        info["build_year"] = year
    if material:
        info["wall_material"] = material
    if info:
        return info, mingkh_url, domclick_url

    # 4. Реформа ЖКХ (reformagkh.ru)
    rgkh_fields, rgkh_url = get_building_from_reformagkh(city, street, house, block, settlement)
    if rgkh_fields:
        return rgkh_fields, rgkh_url, domclick_url

    return info, mingkh_url, domclick_url


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
