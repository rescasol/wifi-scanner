# 📡 WiFi Scanner

Escàner de dispositius WiFi amb interfície web i alertes Telegram. Detecta tots els dispositius connectats a la teva xarxa, mostra informació detallada (IP, MAC, fabricant, OS), permet marcar-los com a coneguts i envia notificacions quan apareix un dispositiu nou o desconegut.

---

## Funcionalitats

- **Escaneig de xarxa** — detecta IP, MAC, nom d'equip, fabricant i sistema operatiu
- **Base de dades local** — recorda tots els dispositius vistos, quan i quantes vegades
- **Dispositius coneguts** — marca els teus dispositius i posa'ls un nom personalitzat
- **Alertes Telegram** — notificació instantània quan es connecta un dispositiu desconegut
- **Monitor continu** — escaneig automàtic cada N segons en segon pla
- **Interfície web** — panel accessible des de qualsevol dispositiu de la xarxa
- **CLI** — tots els comandos disponibles també per terminal

---

## Instal·lació (un sol comando)

### Windows

> Requereix [Python 3.10+](https://www.python.org/downloads/) i [nmap + Npcap](https://nmap.org/download.html) instal·lats prèviament.

Fes clic dret a `install.bat` → **Executar com a administrador**

O des d'una consola d'administrador:
```cmd
install.bat
```

### Linux / Raspberry Pi

```bash
bash install.sh
```

L'script instal·la automàticament `nmap` si no està present (requereix `apt`).

---

## Configuració

Edita `config.yml` (creat automàticament durant la instal·lació):

```yaml
# Rang de xarxa — adapta-ho a la teva IP
# Windows: obre cmd → ipconfig → busca "Puerta de enlace predeterminada"
# Linux:   ip route | grep -v default
network: "192.168.1.0/24"

# Interval en segons entre escanejos en mode monitor
monitor_interval: 60

# Bot de Telegram per a alertes (opcional)
telegram:
  token: "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
  chat_id: "123456789"
```

### Com trobar el rang de xarxa

| Sistema | Comando |
|---|---|
| Windows | `ipconfig` → busca "Puerta de enlace" (ex: `192.168.1.1` → rang: `192.168.1.0/24`) |
| Linux / RPi | `ip route \| grep -v default` |

### Configurar alertes Telegram (opcional)

1. Obre Telegram → busca **@BotFather** → envia `/newbot`
2. Copia el **token** que et dona (format: `123456:ABC-DEF...`)
3. Envia un missatge al teu bot nou
4. Obre `https://api.telegram.org/bot<TOKEN>/getUpdates` i busca `"chat":{"id": XXXXXXX}`
5. Posa el token i el chat_id a `config.yml`
6. Prova-ho amb el botó Telegram de la interfície web

> Per rebre alertes en un **grup**: afegeix el bot al grup i el chat_id serà negatiu (ex: `-1001234567890`)

---

## Ús

### Interfície web (recomanada)

**Windows** (com a Administrador):
```cmd
run.bat
```

**Linux / Raspberry Pi**:
```bash
sudo ./run.sh
```

Obre el navegador a **`http://localhost:5000`**

Si uses una Raspberry Pi, pots accedir des de qualsevol dispositiu de la xarxa:
**`http://IP_DE_LA_RASPI:5000`**

#### Elements de la interfície

| Element | Descripció |
|---|---|
| **Escanejar** | Escaneig puntual de la xarxa |
| **Monitor** | Escaneig automàtic continu + alertes Telegram |
| **Telegram** (icona) | Prova si les notificacions funcionen |
| ● verd parpellejant | Dispositiu connectat en aquest moment |
| ● gris | Dispositiu desconnectat (recordat) |
| Badge verd "Conegut" | Dispositiu marcat com a de confiança |
| Badge vermell "Desconegut" | Dispositiu no identificat |
| ✓ (acció) | Marcar com a conegut |
| ✗ (acció) | Desmarcar |
| ✏ (acció) | Canviar nom / àlies |
| 🗑 (acció) | Eliminar de la base de dades |
| Filtres | Tots / En línia / Desconeguts |
| Cercador | Filtra per IP, nom, MAC, fabricant |

### CLI (terminal)

```bash
# Escaneig puntual
sudo python wifi_scanner.py scan

# Escaneig amb detecció de sistema operatiu (necessita root/admin)
sudo python wifi_scanner.py scan --aggressive

# Llistar tots els dispositius registrats
python wifi_scanner.py list

# Llistar només els que estan en línia ara
python wifi_scanner.py list --online-only

# Marcar dispositiu com a conegut (per IP, MAC o nom)
python wifi_scanner.py mark 192.168.1.5
python wifi_scanner.py mark 192.168.1.5 --alias "El meu mòbil"
python wifi_scanner.py mark AA:BB:CC:DD:EE:FF --alias "Ruter"

# Canviar el nom d'un dispositiu
python wifi_scanner.py alias 192.168.1.10 "Chromecast sala"

# Desmarcar dispositiu
python wifi_scanner.py unmark AA:BB:CC:DD:EE:FF

# Monitor continu (Ctrl+C per aturar)
sudo python wifi_scanner.py monitor
sudo python wifi_scanner.py monitor --interval 30

# Provar connexió Telegram
python wifi_scanner.py test-telegram

# Eliminar dispositiu de la base de dades
python wifi_scanner.py delete 192.168.1.99
```

---

## Notes per plataforma

### Windows

- Executa sempre com a **Administrador** per detectar adreces MAC
- Necessita **Npcap** (s'instal·la juntament amb nmap des de [nmap.org](https://nmap.org/download.html))
- Si no tens MAC addresses, segurament falta Npcap o permisos d'administrador

### Raspberry Pi 5

- Executa amb `sudo` per a escaneig complet
- El servidor web és accessible des de tota la xarxa local automàticament
- Per iniciar automàticament en arrencar, afegeix a `/etc/rc.local`:
  ```bash
  cd /ruta/al/wifi-scanner && sudo ./run.sh &
  ```
- O millor, crea un servei systemd:
  ```bash
  sudo nano /etc/systemd/system/wifi-scanner.service
  ```
  ```ini
  [Unit]
  Description=WiFi Scanner
  After=network.target

  [Service]
  WorkingDirectory=/ruta/al/wifi-scanner
  ExecStart=/ruta/al/wifi-scanner/.venv/bin/python /ruta/al/wifi-scanner/app.py
  Restart=always
  User=root

  [Install]
  WantedBy=multi-user.target
  ```
  ```bash
  sudo systemctl enable wifi-scanner
  sudo systemctl start wifi-scanner
  ```

---

## Estructura de fitxers

```
wifi-scanner/
├── app.py                # Servidor web Flask (interfície web)
├── wifi_scanner.py       # Lògica d'escaneig + CLI
├── templates/
│   └── index.html        # Interfície web (HTML/JS)
├── config.yml            # La teva configuració (no al git)
├── config.example.yml    # Plantilla de configuració
├── devices.json          # Base de dades de dispositius (no al git)
├── requirements.txt      # Dependències Python
├── install.sh            # Instal·lació Linux/Raspberry Pi
├── install.bat           # Instal·lació Windows
├── run.sh                # Iniciar servidor (Linux/RPi)
└── run.bat               # Iniciar servidor (Windows)
```

---

## Dependències

| Paquet | Ús |
|---|---|
| `python-nmap` | Interfície Python per a nmap |
| `mac-vendor-lookup` | Identificació de fabricant per MAC |
| `flask` | Servidor web per a la interfície |
| `PyYAML` | Lectura de config.yml |
| `requests` | Enviament d'alertes Telegram |
| `rich` | Taules i colors al terminal (CLI) |

Sistema: **nmap** ha d'estar instal·lat al sistema operatiu.

---

## Requisits mínims

| | Windows | Linux / Raspberry Pi |
|---|---|---|
| Python | 3.10+ | 3.10+ |
| nmap | [nmap.org](https://nmap.org/download.html) + Npcap | `sudo apt install nmap` |
| Permisos | Administrador | sudo |
| RAM | ~50 MB | ~30 MB |
