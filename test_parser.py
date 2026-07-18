import sys
import warnings

from utils.format import format_building_fields
from parsers.aggregator import get_building_info
from parsers.dadata import get_dadata_address
from settings import DADATA_API

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    if not DADATA_API:
        raise ValueError("Переменная DADATA_API не задана в .env")
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Уфа Злобина 38/2"

    addr, details = get_dadata_address(query)
    if not addr:
        print("❌ Ошибка: Адрес не найден.")
        sys.exit(1)

    cadastre = details.get("house_cadnum") or details.get("cadnum") or "Не указан"
    street, house = details.get("street"), details.get("house")
    block = details.get("block")

    try:
        lat = float(details.get("geo_lat") or 0) or None
        lon = float(details.get("geo_lon") or 0) or None
    except (TypeError, ValueError):
        lat, lon = None, None

    print(f"✅ Дадата: {addr} | КН: {cadastre} | lat={lat} lon={lon}")

    info, mingkh_url, domclick_url = get_building_info(
        cadastre,
        details.get("city"),
        street,
        house,
        block,
        settlement=details.get("settlement"),
        city_district=details.get("city_district"),
        lat=lat,
        lon=lon,
        dadata_addr=addr,
        region=details.get("region"),
        region_type=details.get("region_type"),
        area=details.get("area"),
        area_type=details.get("area_type"),
        settlement_type=details.get("settlement_type"),
        street_type=details.get("street_type"),
    )

    print("\n📊 РЕЗУЛЬТАТ:")
    if info:
        print(format_building_fields(info, mingkh_url=mingkh_url, domclick_url=domclick_url))
    else:
        print("Данные не найдены")
