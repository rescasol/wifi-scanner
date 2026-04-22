#!/usr/bin/env python3
"""Flask web UI for WiFi Scanner."""

import json
import threading
import time
import platform
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request

from wifi_scanner import (
    load_config,
    load_devices,
    save_devices,
    scan_network,
    merge_scan_results,
    send_telegram,
    build_alert_message,
    is_admin,
)

app = Flask(__name__)
cfg = load_config()

# ── Shared scan state ──────────────────────────────────────────────────────
_lock = threading.Lock()
_scan_status: dict = {
    "running": False,
    "last_scan": None,
    "error": None,
    "progress": "",
    "found": 0,
}
_monitor_active = False
_monitor_thread: threading.Thread | None = None


# ── Background scan ────────────────────────────────────────────────────────

def _do_scan(network: str, aggressive: bool = False) -> None:
    global _scan_status
    with _lock:
        _scan_status.update(running=True, error=None, progress="Escanejant la xarxa...")

    try:
        scanned = scan_network(network, aggressive=aggressive)
        devices_db = load_devices()
        new_macs, returned_macs = merge_scan_results(devices_db, scanned)
        save_devices(devices_db)

        tg = cfg.get("telegram", {})
        for mac in new_macs:
            d = devices_db[mac]
            if not d.get("known") and tg.get("token") and tg.get("chat_id"):
                send_telegram(tg["token"], tg["chat_id"], build_alert_message(d))

        with _lock:
            _scan_status.update(
                running=False,
                last_scan=datetime.now().isoformat(),
                progress=f"Completat: {len(scanned)} dispositius trobats",
                found=len(scanned),
                error=None,
            )
    except Exception as e:
        with _lock:
            _scan_status.update(
                running=False,
                error=str(e),
                progress=f"Error: {e}",
            )


# ── API ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with _lock:
        status = dict(_scan_status)
    status["monitor_active"] = _monitor_active
    status["network"] = cfg.get("network", "192.168.1.0/24")
    status["platform"] = platform.system()
    status["is_admin"] = is_admin()
    return jsonify(status)


@app.route("/api/devices")
def api_devices():
    devices_db = load_devices()
    result = []
    for mac, d in devices_db.items():
        entry = dict(d)
        entry["id"] = mac
        entry["display_name"] = d.get("alias") or d.get("hostname") or mac
        result.append(entry)
    result.sort(key=lambda x: (not x.get("online", False), x.get("ip", "")))
    return jsonify(result)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    with _lock:
        if _scan_status["running"]:
            return jsonify({"error": "Escaneig ja en curs"}), 409

    data = request.get_json(silent=True) or {}
    network = data.get("network") or cfg.get("network", "192.168.1.0/24")
    aggressive = data.get("aggressive", False)

    t = threading.Thread(target=_do_scan, args=(network, aggressive), daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/device/<path:mac>/mark", methods=["POST"])
def api_mark(mac: str):
    devices_db = load_devices()
    mac = mac.upper()
    if mac not in devices_db:
        return jsonify({"error": "Dispositiu no trobat"}), 404
    devices_db[mac]["known"] = True
    data = request.get_json(silent=True) or {}
    if data.get("alias"):
        devices_db[mac]["alias"] = data["alias"]
    save_devices(devices_db)
    return jsonify({"ok": True})


@app.route("/api/device/<path:mac>/unmark", methods=["POST"])
def api_unmark(mac: str):
    devices_db = load_devices()
    mac = mac.upper()
    if mac not in devices_db:
        return jsonify({"error": "Dispositiu no trobat"}), 404
    devices_db[mac]["known"] = False
    save_devices(devices_db)
    return jsonify({"ok": True})


@app.route("/api/device/<path:mac>/alias", methods=["POST"])
def api_alias(mac: str):
    devices_db = load_devices()
    mac = mac.upper()
    if mac not in devices_db:
        return jsonify({"error": "Dispositiu no trobat"}), 404
    data = request.get_json(silent=True) or {}
    devices_db[mac]["alias"] = data.get("alias", "")
    save_devices(devices_db)
    return jsonify({"ok": True})


@app.route("/api/device/<path:mac>", methods=["DELETE"])
def api_delete(mac: str):
    devices_db = load_devices()
    mac = mac.upper()
    if mac not in devices_db:
        return jsonify({"error": "Dispositiu no trobat"}), 404
    del devices_db[mac]
    save_devices(devices_db)
    return jsonify({"ok": True})


@app.route("/api/monitor/start", methods=["POST"])
def api_monitor_start():
    global _monitor_active, _monitor_thread
    if _monitor_active:
        return jsonify({"error": "Monitor ja actiu"}), 409

    data = request.get_json(silent=True) or {}
    interval = int(data.get("interval") or cfg.get("monitor_interval", 60))
    network = data.get("network") or cfg.get("network", "192.168.1.0/24")

    _monitor_active = True

    def _loop():
        global _monitor_active
        while _monitor_active:
            _do_scan(network)
            for _ in range(interval):
                if not _monitor_active:
                    break
                time.sleep(1)

    _monitor_thread = threading.Thread(target=_loop, daemon=True)
    _monitor_thread.start()
    return jsonify({"ok": True, "interval": interval})


@app.route("/api/monitor/stop", methods=["POST"])
def api_monitor_stop():
    global _monitor_active
    _monitor_active = False
    return jsonify({"ok": True})


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    tg = cfg.get("telegram", {})
    if not tg.get("token") or not tg.get("chat_id"):
        return jsonify({"error": "Falta token o chat_id a config.yml"}), 400
    ok = send_telegram(tg["token"], tg["chat_id"], "✅ <b>WiFi Scanner</b> connectat correctament!")
    if ok:
        return jsonify({"ok": True})
    return jsonify({"error": "Error enviant. Comprova token i chat_id."}), 500


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WiFi Scanner - Interfície web")
    parser.add_argument("--host", default="0.0.0.0", help="Adreça d'escolta (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"Obri el navegador a: http://localhost:{args.port}")
    if not is_admin():
        if platform.system() == "Windows":
            print("AVÍS: Executa com a Administrador per detectar adreces MAC correctament.")
        else:
            print("AVÍS: Executa amb sudo per detectar adreces MAC correctament.")

    app.run(host=args.host, port=args.port, debug=args.debug)
