#!/bin/bash
# Inicia el servidor web de WiFi Scanner
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$DIR/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: entorn virtual no trobat. Executa primer: bash install.sh"
    exit 1
fi

if [ ! -f "$DIR/config.yml" ]; then
    echo "Error: config.yml no trobat. Copia config.example.yml a config.yml i configura'l."
    exit 1
fi

exec sudo "$PYTHON" "$DIR/app.py" "$@"
