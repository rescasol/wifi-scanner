@echo off
setlocal EnableDelayedExpansion

echo.
echo =========================================
echo      WiFi Scanner - Installacio
echo =========================================
echo.

:: Comprovar que s'executa com a Administrador
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
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] nmap no trobat!
    echo.
    echo         Cal installar nmap + Npcap per detectar dispositius.
    echo         Descarrega'l de: https://nmap.org/download.html
    echo         Durant la installacio, marca "Install Npcap".
    echo.
    echo         Un cop installat nmap, torna a executar aquest fitxer.
    echo.
    pause
    exit /b 1
)
echo [OK] nmap trobat

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
pip install --upgrade pip --quiet
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
    echo      Edita'l amb: notepad config.yml
) else (
    echo [OK] config.yml ja existeix
)

:: Resum
echo.
echo =========================================
echo   Installacio completada correctament!
echo =========================================
echo.
echo   1. Edita la configuracio:
echo        notepad config.yml
echo.
echo   2. Inicia el servidor (com a Administrador):
echo        run.bat
echo.
echo   3. Obre el navegador a:
echo        http://localhost:5000
echo.
pause
