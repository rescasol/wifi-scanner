#!/bin/bash
# WiFi Scanner — instal·lació per a Linux / Raspberry Pi
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}▶ $*${NC}"; }
success() { echo -e "${GREEN}✓ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $*${NC}"; }
error()   { echo -e "${RED}✗ $*${NC}"; exit 1; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       📡 WiFi Scanner — Setup        ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ── Python ─────────────────────────────────────────────────────────────────
info "Comprovant Python 3.10+..."
if ! command -v python3 &>/dev/null; then
    error "Python3 no trobat. Instal·la'l amb: sudo apt install python3 python3-pip python3-venv"
fi

PY_VER=$(python3 -c 'import sys; print(sys.version_info[:2] >= (3,10))')
if [ "$PY_VER" != "True" ]; then
    error "Cal Python 3.10 o superior. Versió actual: $(python3 --version)"
fi
success "Python $(python3 --version | cut -d' ' -f2)"

# ── nmap ───────────────────────────────────────────────────────────────────
info "Comprovant nmap..."
if ! command -v nmap &>/dev/null; then
    warn "nmap no trobat — instal·lant..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y nmap
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y nmap
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm nmap
    else
        error "No he pogut instal·lar nmap. Fes-ho manualment: sudo apt install nmap"
    fi
fi
success "nmap $(nmap --version | head -1 | awk '{print $3}')"

# ── Entorn virtual ─────────────────────────────────────────────────────────
info "Creant entorn virtual (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    success "Entorn virtual creat"
else
    success "Entorn virtual ja existeix"
fi

# ── Paquets Python ─────────────────────────────────────────────────────────
info "Instal·lant paquets Python..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet
success "Paquets instal·lats"

# ── Config ─────────────────────────────────────────────────────────────────
if [ ! -f "config.yml" ]; then
    cp config.example.yml config.yml
    warn "Fitxer config.yml creat. Edita'l abans d'iniciar:"
    echo    "     nano config.yml"
else
    success "config.yml ja existeix"
fi

# ── Permisos ───────────────────────────────────────────────────────────────
chmod +x run.sh 2>/dev/null || true

# ── Resum ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}✅  Instal·lació completada!${NC}"
echo ""
echo -e "  ${BOLD}1.${NC} Edita la configuració:"
echo    "       nano config.yml"
echo ""
echo -e "  ${BOLD}2.${NC} Inicia el servidor web:"
echo    "       sudo ./run.sh"
echo ""
echo -e "  ${BOLD}3.${NC} Obre el navegador a:"
echo -e "       ${CYAN}http://localhost:5000${NC}"
echo ""
