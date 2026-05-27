import sys
import warnings

from parser_utils import get_dadata_address, get_year_from_mingkh_smart
from settings import require_dadata_api

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    require_dadata_api()
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Уфа Злобина 38/2"
    
    # Шаг 1
    addr, details = get_dadata_address(query)
    if not addr:
        print("❌ Ошибка: Адрес не найден.")
        sys.exit(1)
        
    cadastre = details.get("house_cadnum") or details.get("cadnum") or "Не указан"
    city = details.get("city") or details.get("settlement")
    street, house = details.get("street"), details.get("house")
    block = details.get("block")
    
    print(f"✅ Дадата: {addr} | КН: {cadastre}")
    
    # Шаг 2
    year, mat, url = get_year_from_mingkh_smart(
        cadastre, details.get("city"), street, house, block, settlement=details.get("settlement")
    )
    
    print(f"\n📊 РЕЗУЛЬТАТ:")
    print(f"📅 Год: {year or 'Не найден'}")
    print(f"🧱 Материал: {mat or 'Нет данных'}")
    print(f"🔗 Источник: {url or 'Нет данных'}")