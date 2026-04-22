@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

echo.
echo ╔══════════════════════════════════════╗
echo ║       📡 WiFi Scanner — Setup        ║
echo ╚══════════════════════════════════════╝
echo.

:: ── Comprovar que s'executa com a Administrador ───────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [AVÍS] No s'està executant com a Administrador.
    echo        Per detectar adreces MAC correctament, fes clic dret
    echo        a install.bat i tria "Executar com a administrador".
    echo.
    pause
)

:: ── Python ─────────────────────────────────────────────────────────────────
echo [1/5] Comprovant Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python no trobat!
    echo         Descarrega'l de: https://www.python.org/downloads/
    echo         Marca "Add Python to PATH" durant la instal.lacio.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ── nmap ───────────────────────────────────────────────────────────────────
echo [2/5] Comprovant nmap...
nmap --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [AVÍS] nmap no trobat!
    echo.
    echo        Cal instal.lar nmap + Npcap per detectar dispositius.
    echo        Descarrega nmap de: https://nmap.org/download.html
    echo        Durant la instal.lacio, marca "Install Npcap".
    echo.
    echo        Un cop instal.lat nmap, torna a executar aquest fitxer.
    pause
    exit /b 1
)
echo [OK] nmap trobat

:: ── Entorn virtual ─────────────────────────────────────────────────────────
echo [3/5] Creant entorn virtual (.venv)...
if not exist ".venv\" (
    python -m venv .venv
    if %errorLevel% neq 0 (
        echo [ERROR] No s'ha pogut crear l'entorn virtual.
        pause & exit /b 1
    )
    echo [OK] Entorn virtual creat
) else (
    echo [OK] Entorn virtual ja existeix
)

:: ── Paquets Python ─────────────────────────────────────────────────────────
echo [4/5] Instal.lant paquets Python...
call .venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorLevel% neq 0 (
    echo [ERROR] Problema instal.lant paquets. Comprova la connexio a internet.
    pause & exit /b 1
)
echo [OK] Paquets instal.lats

:: ── Config ─────────────────────────────────────────────────────────────────
echo [5/5] Configuracio...
if not exist "config.yml" (
    copy config.example.yml config.yml >nul
    echo [OK] config.yml creat — edita'l abans d'iniciar
) else (
    echo [OK] config.yml ja existeix
)

:: ── Resum ──────────────────────────────────────────────────────────────────
echo.
echo ╔══════════════════════════════════════════════╗
echo ║  ✅  Instal.lacio completada!                ║
echo ╚══════════════════════════════════════════════╝
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
