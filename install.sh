#!/usr/bin/env bash
set -e

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "============================================"
echo "Установка завершена."
echo "Активируй окружение:"
echo "  source venv/bin/activate"
echo "Запуск:"
echo "  ./run_dev.sh"
echo "============================================"
chmod +x install.sh
