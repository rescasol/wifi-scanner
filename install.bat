@echo off
setlocal EnableDelayedExpansion

echo.
echo =========================================
echo      WiFi Scanner - Installacio
echo =========================================
echo.

:: Comprovar Administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [AVIS] No s'esta executant com a Administrador.
    echo        Per detectar adreces MAC correctament, fes clic dret
    echo        a install.bat i tria "Executar como administrador".
    echo.
    pause
)

:: 1/5 - Python
echo [1/5] Comprovant Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Python no trobat!
    echo         Descarrega'l de: https://www.python.org/downloads/
    echo         Marca "Add Python to PATH" durant la installacio.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: 2/5 - nmap
echo [2/5] Comprovant nmap...
nmap --version >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] nmap trobat
    goto :nmap_ok
)

echo [INFO] nmap no trobat. Installant automaticament...
echo.

:: Intent 1: winget (Windows 10/11 modern)
winget --version >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Installant nmap via winget (pot trigar 1-2 minuts)...
    winget install --id Insecure.Nmap --silent --accept-package-agreements --accept-source-agreements
    if %errorLevel% equ 0 (
        echo [OK] nmap installat via winget
        goto :nmap_refresh
    )
    echo [INFO] winget fallat, provant descarrega directa...
)

:: Intent 2: descarregar installer directament amb PowerShell
echo [INFO] Descarregant installer de nmap.org...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://nmap.org/dist/nmap-7.95-setup.exe' -OutFile '%TEMP%\nmap-setup.exe' -UseBasicParsing"
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] No s'ha pogut descarregar nmap.
    echo         Comprova la connexio a internet o installa'l manualment:
    echo         https://nmap.org/download.html
    echo         (marca "Install Npcap" durant la installacio)
    echo.
    pause
    exit /b 1
)

echo [INFO] Executant installer de nmap (segueix les instruccions en pantalla)...
echo        Accepta totes les opcions per defecte i inclou Npcap.
"%TEMP%\nmap-setup.exe"
del "%TEMP%\nmap-setup.exe" >nul 2>&1

:nmap_refresh
:: Afegir nmap al PATH de la sessio actual
set "NMAP_PATH=C:\Program Files (x86)\Nmap"
if exist "%NMAP_PATH%\nmap.exe" set "PATH=%NMAP_PATH%;%PATH%"

nmap --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [AVIS] nmap installat pero no accessible en aquesta sessio.
    echo        Tanca i obre una nova finestra d'administrador i torna a executar.
    pause
    exit /b 1
)
echo [OK] nmap installat correctament

:nmap_ok

:: 3/5 - Entorn virtual
echo [3/5] Creant entorn virtual (.venv)...
if not exist ".venv\" (
    python -m venv .venv
    if %errorLevel% neq 0 (
        echo [ERROR] No s'ha pogut crear l'entorn virtual.
        pause
        exit /b 1
    )
    echo [OK] Entorn virtual creat
) else (
    echo [OK] Entorn virtual ja existeix
)

:: 4/5 - Paquets Python
echo [4/5] Installant paquets Python...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorLevel% neq 0 (
    echo [ERROR] Problema installant paquets. Comprova la connexio a internet.
    pause
    exit /b 1
)
echo [OK] Paquets installats

:: 5/5 - Config
echo [5/5] Configuracio...
if not exist "config.yml" (
    copy config.example.yml config.yml >nul
    echo [OK] config.yml creat
) else (
    echo [OK] config.yml ja existeix
)

:: Resum
echo.
echo =========================================
echo   Installacio completada correctament!
echo =========================================
echo.
echo   Passos seguents:
echo.
echo   1. Edita la configuracio (xarxa + Telegram):
echo        notepad config.yml
echo.
echo   2. Inicia el servidor (com a Administrador):
echo        run.bat
echo.
echo   3. Obre el navegador a:
echo        http://localhost:5000
echo.
pause
