#!/bin/bash

# 1. Экспортируем все необходимые ключи
export BOT_TOKEN="8723137175:AAEUe1wwRc1u4v-iyELtwLHiaoCzDkzqjpg"
export DADATA_API="47218163ee0299088ea31b65606f49d06c3fbdeb"
export DADATA_SECRET="c87ef0e5c79734d6bd7dd2d2b9c0ef39cad3e918"

if [ -z "$DADATA_API" ]; then
    echo "⚠️ Переменная DADATA_API в терминале пуста. Пробую прочитать из run.sh..."
    export DADATA_API=$(grep -oP 'export DADATA_API="\K[^"]+' run.sh 2>/dev/null)
fi

# 2. Логика интерактивного ввода адреса
# Если вы запустили `./test.sh "Уфа Ленина 5"`, то скрипт возьмет этот аргумент ($1).
# Если вы запустили просто `./test.sh`, скрипт сам спросит адрес в консоли.
if [ -z "$1" ]; then
    echo "⌨️  Введите адрес для проверки (например: Уфа Заки Валиди 5):"
    read -r user_address
else
    user_address="$1"
fi

# Активируем виртуальное окружение, чтобы были доступны requests и bs4
source .venv/bin/activate

# 3. Запускаем тестовый скрипт и передаем ему адрес, который мы поймали выше
python test_parser.py "$user_address"