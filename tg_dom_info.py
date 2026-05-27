import asyncio
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Загружаем окружение из .env
load_dotenv()

from parser_utils import get_dadata_address, get_year_from_mingkh_smart

# --- НАСТРОЙКА КРУГЛОСУТОЧНОГО ЛОГИРОВАНИЯ ---
if not os.path.exists("logs"):
    os.makedirs("logs")

log_format = "%(asctime)s | %(levelname)s | %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = TimedRotatingFileHandler(
    filename="logs/bot.log", when="midnight", interval=1, encoding="utf-8"
)
file_handler.suffix = "%Y-%m-%d"
file_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console_handler)

# --- ИНИЦИАЛИЗАЦИЯ КЛИЕНТА TG ---
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Критическая ошибка: Переменная BOT_TOKEN не найдена в файле .env!")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


def get_house_data(address: str) -> str:
    """Dadata → МинЖКХ (год постройки, материал стен)."""
    try:
        correct_address, details = get_dadata_address(address)
        
        if not details:
            return "❌ Объект по такому адресу не найден либо сервис верификации временно недоступен."
            
        if not details.get("house"):
            return "❌ Адрес найден, но, пожалуйста, укажите конкретный номер дома или корпуса."
            
        fias_id = details.get("house_fias_id")
        postal_code = details.get("postal_code") or ""
        house_type = details.get("house_type_full", "дом").lower()
        
        cadastre = details.get("house_cadnum") or details.get("cadnum") or "Не указан"
        build_year = None
        wall_material = None
        mingkh_url = None
        
        target_city = details.get("city") or details.get("settlement")
        target_street = details.get("street")
        target_house = details.get("house")
        target_block = details.get("block")
        
        if target_city and target_street and target_house:
            build_year, wall_material, mingkh_url = get_year_from_mingkh_smart(
                cadastre, target_city, target_street, target_house, target_block
            )

        if not build_year:
            build_year = "Нет данных"

        # Ссылка на официальную государственную карточку ГИС ЖКХ по ФИАС ID
        gis_url = f"https://dom.gosuslugi.ru/pds/public/services/fias/house?houseGuid={fias_id}"
        
        # Сборка финального Markdown-отчета для отправки пользователю
        msg = f"🏢 **Объект успешно найден!**\n"
        if "дом" not in house_type:
            msg += f"⚠️ *Внимание: Похоже, это административное или нежилое здание ({house_type}).*\n"
            
        msg += (
            f"📍 `{postal_code} {correct_address}`\n\n"
            f"🔢 **Кадастровый номер:** `{cadastre}`\n"
            f"📅 **Год постройки:** `{build_year}`\n"
        )
        
        if wall_material:
            msg += f"🧱 **Материал стен:** `{wall_material}`\n"
            
        msg += f"🆔 **ID ФИАС:** `{fias_id}`\n\n"
        
        if mingkh_url:
            msg += f"🔗 [Паспорт дома на МинЖКХ]({mingkh_url})\n"
        msg += f"🔗 [Карточка объекта на ГИС ЖКХ]({gis_url})"
        
        return msg

    except Exception as e:
        logging.error(f"Общая ошибка функции get_house_data: {e}")
        return f"⚠️ Ошибка при обработке запроса: {e}"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Отправь мне адрес дома, и я найду год постройки и параметры в базах Dadata и МинЖКХ.")


@dp.message(F.text)
async def handle_address(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "NoUsername"
    logging.info(f"{user.full_name} ({username}) | ID: {user.id} | Запрос: {message.text}")
    
    status_msg = await message.answer("🔍 Собираю технические характеристики объекта...")
    reply_text = get_house_data(message.text)
    
    await status_msg.delete()
    await message.answer(reply_text, parse_mode="Markdown", disable_web_page_preview=True)


async def main():
    logging.info("Бот [tg_dom_info] успешно запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())