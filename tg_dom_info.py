import asyncio
import os
import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from building_format import format_building_telegram
from domclick_auth import COOKIES_FILE, MOBILE_AUTH_FILE, save_cookie, save_mobile_auth
from domclick_utils import is_qrator_blocked
from parser_utils import get_building_info, get_dadata_address
from settings import require_bot_token, ADMIN_ID

# --- ЛОГИРОВАНИЕ ---
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

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=require_bot_token())
dp = Dispatcher()

_DOMCLICK_URL = "https://domclick.ru"
_AWAITING_COOKIE: set[int] = set()


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and str(user_id) == str(ADMIN_ID)


def get_house_data(address: str) -> str:
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
        building_info = {}
        mingkh_url = None
        domclick_url = None

        target_city = details.get("city") or details.get("settlement")
        target_street = details.get("street")
        target_house = details.get("house")
        target_block = details.get("block")

        if target_city and target_street and target_house:
            try:
                lat = float(details.get("geo_lat") or 0) or None
                lon = float(details.get("geo_lon") or 0) or None
            except (TypeError, ValueError):
                lat, lon = None, None

            building_info, mingkh_url, domclick_url = get_building_info(
                cadastre,
                details.get("city"),
                target_street,
                target_house,
                target_block,
                settlement=details.get("settlement"),
                city_district=details.get("city_district"),
                lat=lat,
                lon=lon,
                dadata_addr=correct_address,
                region=details.get("region"),
                region_type=details.get("region_type"),
                area=details.get("area"),
                area_type=details.get("area_type"),
                settlement_type=details.get("settlement_type"),
                street_type=details.get("street_type"),
            )

        gis_url = f"https://dom.gosuslugi.ru/pds/public/services/fias/house?houseGuid={fias_id}"

        msg = "🏢 **Объект успешно найден!**\n"
        if "дом" not in house_type:
            msg += f"⚠️ *Внимание: Похоже, это административное или нежилое здание ({house_type}).*\n"

        msg += f"📍 `{postal_code} {correct_address}`\n\n"
        msg += f"🔢 **Кадастровый номер:** `{cadastre}`\n"

        if building_info:
            msg += format_building_telegram(
                building_info,
                mingkh_url=mingkh_url,
                domclick_url=domclick_url,
            )
        else:
            msg += "📅 **Год постройки:** `Нет данных`\n"

        msg += f"\n🆔 **ID ФИАС:** `{fias_id}`"
        if not domclick_url and not mingkh_url:
            msg += f"\n🔗 [ГИС ЖКХ]({gis_url})"

        return msg

    except Exception as e:
        logging.error(f"Общая ошибка функции get_house_data: {e}")
        return f"⚠️ Ошибка при обработке запроса: {e}"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Отправь мне адрес дома — найду год постройки и характеристики "
        "в Dadata, МинЖКХ и Domclick."
    )


@dp.message(Command("domclick"))
async def cmd_domclick(message: Message):
    """Проверить доступность Domclick и запросить авторизацию."""
    if not _is_admin(message.from_user.id):
        return

    blocked = await asyncio.get_event_loop().run_in_executor(None, is_qrator_blocked)
    if not blocked:
        cookie_ok = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0
        status = "✅ Domclick доступен" + (" (куки есть)" if cookie_ok else " (без куки)")
        await message.answer(status)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть Domclick в браузере", url=_DOMCLICK_URL)
    ]])
    await message.answer(
        "🔒 Domclick заблокирован Qrator.\n\n"
        "1. Нажмите кнопку ниже — откроется Domclick в браузере\n"
        "2. Войдите в аккаунт (если нужно)\n"
        "3. Скопируйте куки из браузера и отправьте командой:\n"
        "`/setcookie <строка куки>`",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@dp.message(Command("setcookie"))
async def cmd_setcookie(message: Message):
    """Сохранить куки Domclick. Использование: /setcookie <cookie string>"""
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: `/setcookie <строка куки>`", parse_mode="Markdown")
        return

    save_cookie(parts[1].strip())
    await message.answer("✅ Куки Domclick обновлены.")


@dp.message(Command("setmobileauth"))
async def cmd_setmobileauth(message: Message):
    """Обновить auth мобильного API (из Charles).
    Формат: /setmobileauth cookie=<...> hash=<...> timestamp=<...>
    Можно передавать только нужные параметры."""
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Использование:\n"
            "`/setmobileauth cookie=<строка> hash=<v1:...> timestamp=<число>`\n\n"
            "Можно передать только нужные параметры.",
            parse_mode="Markdown",
        )
        return

    raw = parts[1].strip()
    cookie = hash_h = timestamp = ""

    cookie_match = re.search(r"cookie=(.+?)(?:\s+hash=|\s+timestamp=|$)", raw, re.DOTALL)
    hash_match = re.search(r"hash=(v1:[a-f0-9]+)", raw)
    ts_match = re.search(r"timestamp=(\d+)", raw)

    if cookie_match:
        cookie = cookie_match.group(1).strip()
    if hash_match:
        hash_h = hash_match.group(1).strip()
    if ts_match:
        timestamp = ts_match.group(1).strip()

    if not any([cookie, hash_h, timestamp]):
        await message.answer("❌ Не найдено ни одного параметра (cookie/hash/timestamp).")
        return

    save_mobile_auth(cookie=cookie, hash_header=hash_h, timestamp=timestamp)
    saved = []
    if cookie:
        saved.append("cookie")
    if hash_h:
        saved.append("hash")
    if timestamp:
        saved.append("timestamp")
    await message.answer(f"✅ Mobile auth обновлён: {', '.join(saved)}.")


@dp.message(F.text)
async def handle_address(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "NoUsername"
    logging.info(f"{user.full_name} ({username}) | ID: {user.id} | Запрос: {message.text}")

    status_msg = await message.answer("🔍 Собираю технические характеристики объекта...")
    reply_text = await asyncio.get_event_loop().run_in_executor(None, get_house_data, message.text)

    await status_msg.delete()
    await message.answer(reply_text, parse_mode="Markdown", disable_web_page_preview=True)


async def main():
    logging.info("Бот [tg_dom_info] успешно запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
