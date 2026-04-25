#!/bin/bash

# Copia .env.example a .env si no existe
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Archivo .env creado. Por favor edítalo y agrega tu token de Telegram."
    exit 1
fi

# Instalar dependencias si no existen
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "Entorno listo. Ejecuta: source venv/bin/activate && python src/bot.py"