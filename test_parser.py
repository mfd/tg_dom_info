import sys
import warnings

from building_format import format_building_fields
from parser_utils import get_building_info, get_dadata_address
from settings import require_dadata_api

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    require_dadata_api()
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Уфа Злобина 38/2"

    addr, details = get_dadata_address(query)
    if not addr:
        print("❌ Ошибка: Адрес не найден.")
        sys.exit(1)

    cadastre = details.get("house_cadnum") or details.get("cadnum") or "Не указан"
    street, house = details.get("street"), details.get("house")
    block = details.get("block")

    print(f"✅ Дадата: {addr} | КН: {cadastre}")

    info, mingkh_url, domclick_url = get_building_info(
        cadastre,
        details.get("city"),
        street,
        house,
        block,
        settlement=details.get("settlement"),
        city_district=details.get("city_district"),
    )

    source_url = domclick_url or mingkh_url
    print("\n📊 РЕЗУЛЬТАТ:")
    if info:
        print(format_building_fields(info, source_url))
    else:
        print("Данные не найдены")
