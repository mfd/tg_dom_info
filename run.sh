#!/bin/bash

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Скопируйте .env.example в .env и укажите ключи."
    exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [ -z "$BOT_TOKEN" ]; then
    echo "⚠️  BOT_TOKEN не задан в .env"
    exit 1
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "⚠️  Ошибка: Виртуальное окружение .venv не найдено!"
    exit 1
fi

echo "🚀 Запуск Telegram-бота tg_dom_info..."
python -u tg_dom_info.py
