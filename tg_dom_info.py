import asyncio
import os
import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from utils.format import format_building_telegram
from parsers.domclick_auth import COOKIES_FILE, MOBILE_AUTH_FILE, save_cookie, save_mobile_auth
from parsers.domclick import is_qrator_blocked, is_qrator_cookies_stale, get_last_suggest_canonical
from parsers.aggregator import get_building_info
from parsers.dadata import get_dadata_address, get_dadata_by_coords
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
_stale_cookie_notified: bool = False


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and str(user_id) == str(ADMIN_ID)


def get_house_data(address: str, is_admin: bool = False) -> str:
    try:
        correct_address, details = get_dadata_address(address)

        if not details:
            return "❌ Объект по такому адресу не найден либо сервис верификации временно недоступен."

        if not details.get("house"):
            return "❌ Адрес найден, но, пожалуйста, укажите конкретный номер дома или корпуса."

        if not details.get("city") and not details.get("settlement"):
            return "❌ Не удалось определить город или населённый пункт. Пожалуйста, укажите адрес полнее, например: <code>Уфа, Ленина, 70</code>"

        city_or_settlement = (details.get("city") or details.get("settlement") or "").lower()
        if city_or_settlement and city_or_settlement not in address.lower():
            return (
                "❌ Укажите город или населённый пункт в запросе.\n"
                f"Например: <code>{(details.get('city') or details.get('settlement'))}, {address}</code>"
            )

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

        # Строка локации: микрорайон (из Domclick canonical) + район (из Dadata)
        location_parts = []
        canonical = get_last_suggest_canonical()
        if canonical:
            for part in canonical.split(","):
                p = part.strip()
                if any(m in p.lower() for m in ("м-н", "мкр", "микрорайон")):
                    location_parts.append(p)
                    break
        city_district = details.get("city_district")
        city_district_type = details.get("city_district_type_full") or details.get("city_district_type") or "район"
        if city_district:
            location_parts.append(f"{city_district} {city_district_type}")
        city_name = details.get("city") or details.get("settlement") or ""
        if city_name:
            location_parts.append(city_name)
        if postal_code:
            location_parts.append(postal_code)
        location_line = ", ".join(location_parts)

        def e(t: str) -> str:
            return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        msg = "<b>Объект успешно найден!</b>\n"
        if "дом" not in house_type:
            msg += f"<i>Внимание: Похоже, это административное или нежилое здание ({e(house_type)}).</i>\n"

        msg += f"<code>{e(correct_address)}</code>\n"
        if location_line:
            msg += f"<code>{e(location_line)}</code>\n"
        msg += "\n"
        if cadastre and cadastre != "Не указан":
            msg += f"<b>Кадастровый номер:</b> <code>{e(cadastre)}</code>\n"

        if building_info:
            msg += format_building_telegram(
                building_info,
                mingkh_url=mingkh_url,
                domclick_url=domclick_url,
            )
        else:
            msg += "<b>Год постройки:</b> <code>Нет данных</code>\n"
            links = []
            if mingkh_url:
                label = "Реформа ЖКХ" if "reformagkh" in mingkh_url else "МинЖКХ"
                links.append(f'<a href="{mingkh_url}">{label}</a>')
            if domclick_url:
                links.append(f'<a href="{domclick_url}">Domclick</a>')
            if links:
                msg += "\n" + " | ".join(links) + "\n"

        if fias_id:
            msg += f'\n<b>ID ФИАС:</b> <code>{e(str(fias_id))}</code>'
        if not domclick_url and not mingkh_url:
            msg += f'\n<a href="{gis_url}">ГИС ЖКХ</a>'

        if is_admin and domclick_url and is_qrator_cookies_stale():
            msg += '\n\n⚠️ <i>Куки Domclick устарели — данные неполные. Обновите через /setcookie</i>'

        return msg

    except Exception as e:
        logging.error(f"Общая ошибка функции get_house_data: {e}")
        return f"⚠️ Ошибка при обработке запроса: {e}"


async def _notify_admin_if_stale() -> None:
    global _stale_cookie_notified
    if _stale_cookie_notified or not ADMIN_ID or not is_qrator_cookies_stale():
        return
    _stale_cookie_notified = True
    try:
        await bot.send_message(
            ADMIN_ID,
            "⚠️ <b>Куки Domclick устарели</b> — данные об объектах неполные.\n\n"
            "Обнови куки через /setcookie",
            parse_mode="HTML",
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить уведомление админу: {e}")


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
        if ADMIN_ID is None:
            await message.answer("⚠️ ADMIN_ID не задан в настройках бота.")
        else:
            await message.answer("⛔ У вас нет прав администратора.")
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
        "🔒 Domclick заблокирован Qrator — нужны свежие куки\\.\n\n"
        "Qrator хранит bypass\\-токен в HttpOnly\\-куках, поэтому `document.cookie` не поможет\\. "
        "Нужно копировать из Network:\n\n"
        "1\\. Нажмите кнопку ниже — откроется domclick\\.ru\n"
        "2\\. Откройте DevTools: `F12` или `Cmd+Option+I` на Mac\n"
        "3\\. Перейдите на вкладку *Network*\n"
        "4\\. Обновите страницу `F5`\n"
        "5\\. Кликните на любой запрос к `domclick.ru`\n"
        "6\\. Справа: *Headers* → *Request Headers* → найдите строку `cookie:`\n"
        "7\\. Скопируйте всё значение целиком \\(правая кнопка → Copy value\\)\n\n"
        "Затем отправьте боту:\n"
        "`/setcookie <вставленная строка>`",
        parse_mode="MarkdownV2",
        reply_markup=kb,
    )


@dp.message(Command("setcookie"))
async def cmd_setcookie(message: Message):
    """Сохранить куки Domclick. Использование: /setcookie <cookie string>"""
    if not _is_admin(message.from_user.id):
        if ADMIN_ID is None:
            await message.answer("⚠️ ADMIN_ID не задан в настройках бота.")
        else:
            await message.answer("⛔ У вас нет прав администратора.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Как получить куки Domclick:\n\n"
            "1. Открой <a href=\"https://domclick.ru\">domclick.ru</a> в браузере\n"
            "2. <code>F12</code> → вкладка <b>Network</b>\n"
            "3. Обнови страницу <code>F5</code>\n"
            "4. Кликни на любой запрос к <code>domclick.ru</code>\n"
            "5. Справа: <b>Headers → Request Headers → cookie:</b>\n"
            "6. Правая кнопка → <b>Copy value</b>\n\n"
            "Затем отправь:\n<code>/setcookie </code><i>вставленная строка</i>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    global _stale_cookie_notified
    save_cookie(parts[1].strip())
    _stale_cookie_notified = False
    await message.answer("✅ Куки Domclick обновлены.")


@dp.message(Command("setmobileauth"))
async def cmd_setmobileauth(message: Message):
    """Обновить auth мобильного API (из Charles).
    Формат: /setmobileauth cookie=<...> hash=<...> timestamp=<...>
    Можно передавать только нужные параметры."""
    if not _is_admin(message.from_user.id):
        if ADMIN_ID is None:
            await message.answer("⚠️ ADMIN_ID не задан в настройках бота.")
        else:
            await message.answer("⛔ У вас нет прав администратора.")
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


@dp.message(F.location)
async def handle_location(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    status_msg = await message.answer("🔍 Определяю адрес по координатам...")

    admin = _is_admin(message.from_user.id)

    def resolve():
        addr, details = get_dadata_by_coords(lat, lon)
        if not addr or not details.get("house"):
            return "❌ Не удалось определить адрес дома по этой геолокации. Попробуйте выбрать точку поближе к входу в дом."
        return get_house_data(addr, is_admin=admin)

    reply_text = await asyncio.get_event_loop().run_in_executor(None, resolve)
    await status_msg.delete()
    await message.answer(reply_text, parse_mode="HTML", disable_web_page_preview=True)
    await _notify_admin_if_stale()


@dp.message(F.text)
async def handle_address(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "NoUsername"
    logging.info(f"{user.full_name} ({username}) | ID: {user.id} | Запрос: {message.text}")

    admin = _is_admin(user.id)
    status_msg = await message.answer("🔍 Собираю технические характеристики объекта...")
    reply_text = await asyncio.get_event_loop().run_in_executor(
        None, get_house_data, message.text, admin
    )

    await status_msg.delete()
    await message.answer(reply_text, parse_mode="HTML", disable_web_page_preview=True)
    await _notify_admin_if_stale()


async def main():
    logging.info("Бот [tg_dom_info] успешно запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
