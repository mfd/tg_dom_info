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

if [ -z "$DADATA_API" ]; then
    echo "⚠️  DADATA_API не задан в .env"
    exit 1
fi

if [ -z "$1" ]; then
    echo "⌨️  Введите адрес для проверки (например: Уфа Заки Валиди 5):"
    read -r user_address
else
    user_address="$1"
fi

source .venv/bin/activate
python test_parser.py "$user_address"
