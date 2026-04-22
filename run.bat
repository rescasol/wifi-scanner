@echo off
:: Inicia el servidor web de WiFi Scanner (executa com a Administrador)

if not exist ".venv\" (
    echo Error: entorn virtual no trobat. Executa primer install.bat
    pause
    exit /b 1
)
if not exist "config.yml" (
    echo Error: config.yml no trobat. Copia config.example.yml a config.yml i configura'l.
    pause
    exit /b 1
)

echo Iniciant WiFi Scanner...
echo Obre el navegador a: http://localhost:5000
echo Prem Ctrl+C per aturar.
echo.
call .venv\Scripts\activate.bat
python app.py %*
pause
