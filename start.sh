#!/bin/bash

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Создаю виртуальное окружение..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
mkdir -p logs

echo "Запускаю мониторинг USB..."
python main.py monitor
