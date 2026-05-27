import asyncio
import os
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
# Бот автоматически заберет токен из переменной окружения "BOT_TOKEN", которую вы укажете в панели Render
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка: если вы забыли указать переменную на хостинге, бот сразу сообщит об этом в логи
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Критическая ошибка: Переменная окружения 'BOT_TOKEN' не задана в настройках хостинга!")

# Инициализация бота напрямую (без прокси, так как на Render нет ограничений белого списка)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

def get_house_data_mingkh(address: str) -> str:
    """Функция ищет дом на МинЖКХ и вытаскивает характеристики из таблицы результатов"""
    search_url = "https://mingkh.ru/search/"
    params = {"address": address, "searchtype": "house"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        # 1. Поиск по адресу
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return "⚠️ Не удалось подключиться к базе данных МинЖКХ."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем таблицу результатов поиска
        table = soup.find('table', class_='table')
        if not table:
            return "❌ Дом по такому адресу не найден. Попробуйте ввести точнее (Город, улица, дом)."
            
        # Находим ВСЕ ссылки внутри таблицы, которые ведут на профиль дома (они содержат /houses/)
        house_link_element = None
        for a_tag in table.find_all('a', href=True):
            if "/houses/" in a_tag['href']:
                house_link_element = a_tag
                break # Нам нужен самый первый точный результат
                
        if not house_link_element:
            return "❌ Адрес найден в таблице, но не удалось извлечь ссылку на паспорт дома."
            
        # Формируем прямую ссылку на страницу дома
        house_url = f"https://mingkh.ru{house_link_element['href']}"
        
        # 2. Переход на страницу конкретного дома
        house_res = requests.get(house_url, headers=headers, timeout=10)
        house_soup = BeautifulSoup(house_res.text, 'html.parser')
        
        cadastre = "Не указан"
        build_year = "Нет данных"
        
        # Разбираем технические характеристики на странице самого дома
        dl_list = house_soup.find_all('dl', class_='dl-horizontal')
        for dl in dl_list:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                text_label = dt.text.strip().lower()
                if "кадастровый номер" in text_label:
                    cadastre = dd.text.strip()
                elif "год постройки" in text_label or "ввода в эксплуатацию" in text_label:
                    build_year = dd.text.strip()
        
        # Забираем точный красивый адрес, который определил сам сайт
        correct_address = house_link_element.text.strip()
        
        return (
            f"🏢 **Дом успешно найден!**\n"
            f"📍 `{correct_address}`\n\n"
            f"🔢 **Кадастровый номер:** `{cadastre}`\n"
            f"📅 **Год постройки:** `{build_year}`\n\n"
            f"🔗 [Ссылка на паспорт дома]({house_url})"
        )

    except Exception as e:
        return f"⚠️ Ошибка при обработке запроса: {e}"
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Отправь мне адрес дома (например: *Москва, Тверская 8*),\n"
        "и я найду его кадастровый номер и год постройки через базу МинЖКХ."
    )

@dp.message(F.text)
async def handle_address(message: Message):
    status_msg = await message.answer("🔍 Ищу паспорт дома на МинЖКХ...")
    reply_text = get_house_data_mingkh(message.text)
    await status_msg.delete()
    await message.answer(reply_text, parse_mode="Markdown")

async def main():
    print("Бот [tg_dom_info] успешно запущен на Render.com...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())