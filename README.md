# tg_dom_info

Telegram-бот для получения технических характеристик жилых домов по адресу.

Источники данных: **Domclick** (основной), **МинЖКХ**, **Реформа ЖКХ**. Адрес нормализуется через **Dadata**.

## Что умеет

- Год постройки, материал стен, этажность, количество квартир и подъездов
- Тип водоснабжения, отопления, перекрытий и другие характеристики
- Поиск по текстовому адресу или геолокации
- Ссылки на Domclick и МинЖКХ

## Переменные окружения

Скопируй `.env.example` в `.env` и заполни:

```
BOT_TOKEN=       # токен бота от @BotFather
DADATA_API=      # ключ API от dadata.ru
DADATA_SECRET=   # секрет от dadata.ru
ADMIN_ID=        # Telegram ID администратора (числовой)
```

`ADMIN_ID` — получить можно у @userinfobot. Администратор получает уведомления о протухших куках и имеет доступ к командам `/setcookie`, `/domclick`.

## Установка на сервере

```bash
git clone https://github.com/mfd/tg_dom_info.git
cd tg_dom_info

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
nano .env  # заполнить переменные
```

## Запуск через systemd

Создай файл сервиса (`/etc/systemd/system/tg_dom_info.service`):

```ini
[Unit]
Description=tg_dom_info Telegram Bot
After=network.target

[Service]
Type=simple
User=tg_dom_info
WorkingDirectory=/opt/bots/tg_dom_info
EnvironmentFile=/opt/bots/tg_dom_info/.env
ExecStart=/opt/bots/tg_dom_info/.venv/bin/python -u tg_dom_info.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/opt/bots/tg_dom_info/logs/bot.log
StandardError=append:/opt/bots/tg_dom_info/logs/bot.log

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable tg_dom_info
systemctl start tg_dom_info
```

## Обновление

```bash
cd /opt/bots/tg_dom_info
git pull
systemctl restart tg_dom_info
```

## Управление сервисом

```bash
systemctl status tg_dom_info    # статус
systemctl restart tg_dom_info   # перезапуск
systemctl stop tg_dom_info      # остановка
journalctl -u tg_dom_info -f    # логи в реальном времени
tail -f logs/bot.log            # логи из файла
```

## Куки Domclick

Domclick защищён Qrator — для получения полных данных нужны браузерные куки. Datacenter IP (VPS) не может получить их автоматически, поэтому куки копируются вручную с браузера на локальной машине.

**Как обновить куки:**

1. Открой [domclick.ru](https://domclick.ru) в браузере
2. `F12` → вкладка **Network**
3. Обнови страницу `F5`
4. Кликни на любой запрос к `domclick.ru`
5. Справа: **Headers → Request Headers → cookie:**
6. Правая кнопка → **Copy value**
7. Отправь боту: `/setcookie <вставленная строка>`

Бот сам пришлёт уведомление администратору когда куки протухнут.

**Без кук** бот всё равно работает — показывает данные из МинЖКХ и Реформы ЖКХ, и ссылку на Domclick.
