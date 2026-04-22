#!/usr/bin/env python3
"""WiFi Device Scanner with Telegram notifications."""

import json
import time
import argparse
import sys
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional


def is_admin() -> bool:
    """Return True if the process has admin/root privileges."""
    try:
        if platform.system() == "Windows":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False

import nmap
import yaml
import requests
from mac_vendor_lookup import MacLookup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DEVICES_FILE = BASE_DIR / "devices.json"
CONFIG_FILE = BASE_DIR / "config.yml"

console = Console()
_mac_lookup: Optional[MacLookup] = None


# ── Config ─────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        console.print(f"[red]No es troba el fitxer de configuració: {CONFIG_FILE}[/red]")
        console.print("Copia config.example.yml a config.yml i omple les dades.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f)
    return cfg


# ── Device store ───────────────────────────────────────────────────────────

def load_devices() -> dict:
    if DEVICES_FILE.exists():
        with open(DEVICES_FILE) as f:
            return json.load(f)
    return {}


def save_devices(devices: dict) -> None:
    with open(DEVICES_FILE, "w") as f:
        json.dump(devices, f, indent=2, ensure_ascii=False, default=str)


# ── MAC vendor lookup ──────────────────────────────────────────────────────

def get_mac_lookup() -> MacLookup:
    global _mac_lookup
    if _mac_lookup is None:
        _mac_lookup = MacLookup()
        try:
            _mac_lookup.update_vendors()
        except Exception:
            pass  # use cached db if offline
    return _mac_lookup


def get_manufacturer(mac: str) -> str:
    if not mac:
        return ""
    try:
        return get_mac_lookup().lookup(mac)
    except Exception:
        return ""


# ── Telegram ───────────────────────────────────────────────────────────────

def send_telegram(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.ok
    except Exception as e:
        console.print(f"[red]Error Telegram: {e}[/red]")
        return False


def build_alert_message(device: dict) -> str:
    lines = ["🚨 <b>Nou dispositiu detectat a la xarxa!</b>"]
    if device.get("hostname"):
        lines.append(f"🖥  Nom: <code>{device['hostname']}</code>")
    lines.append(f"📡 IP: <code>{device['ip']}</code>")
    if device.get("mac"):
        lines.append(f"🔗 MAC: <code>{device['mac']}</code>")
    if device.get("manufacturer"):
        lines.append(f"🏭 Fabricant: {device['manufacturer']}")
    if device.get("os"):
        lines.append(f"💻 OS: {device['os']}")
    lines.append(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    return "\n".join(lines)


# ── Network scan ───────────────────────────────────────────────────────────

def scan_network(network: str, aggressive: bool = False) -> list[dict]:
    nm = nmap.PortScanner()
    console.print(f"[cyan]Escanejant {network}...[/cyan]")

    # -sn: ping scan, no port scan (fast)
    # --script nbstat: NetBIOS hostnames on LAN
    # -O: OS detection (needs root, optional)
    args = "-sn --script nbstat"
    if aggressive and is_admin():
        args += " -O"

    scan_kwargs: dict = {"hosts": network, "arguments": args}
    # sudo flag only works on Linux/macOS; skip on Windows
    if platform.system() != "Windows" and not is_admin():
        scan_kwargs["sudo"] = True

    try:
        nm.scan(**scan_kwargs)
    except nmap.PortScannerError as e:
        console.print(f"[red]Error nmap: {e}[/red]")
        if platform.system() == "Windows":
            console.print("[yellow]Executa el programa com a Administrador per a millors resultats.[/yellow]")
        else:
            console.print("[yellow]Prova executar amb sudo per a millors resultats.[/yellow]")
        raise RuntimeError(str(e)) from e

    devices = []
    for host in nm.all_hosts():
        info = nm[host]
        addrs = info.get("addresses", {})

        ip = addrs.get("ipv4", host)
        mac = addrs.get("mac", "").upper()
        hostname = info.hostname() or ""

        # Try NetBIOS name from script
        nb_name = ""
        for script in info.get("hostscript", []):
            if script.get("id") == "nbstat":
                output = script.get("output", "")
                for line in output.splitlines():
                    line = line.strip()
                    if "<00>" in line and "GROUP" not in line:
                        nb_name = line.split("<")[0].strip()
                        break

        effective_hostname = nb_name or hostname

        # OS detection
        os_name = ""
        osmatch = info.get("osmatch", [])
        if osmatch:
            best = osmatch[0]
            os_name = best.get("name", "")

        manufacturer = get_manufacturer(mac)

        devices.append({
            "ip": ip,
            "mac": mac,
            "hostname": effective_hostname,
            "manufacturer": manufacturer,
            "os": os_name,
        })

    console.print(f"[green]Dispositius trobats: {len(devices)}[/green]")
    return devices


# ── Device merging ─────────────────────────────────────────────────────────

def merge_scan_results(devices_db: dict, scanned: list[dict]) -> tuple[list[str], list[str]]:
    """
    Update DB with scan results.
    Returns (new_macs, returned_macs) where returned_macs were previously absent.
    """
    now = datetime.now().isoformat()
    new_macs = []
    returned_macs = []

    # Mark all existing as not seen in this scan
    seen_this_scan = set()

    for d in scanned:
        mac = d["mac"] or d["ip"]  # use IP as key if no MAC (e.g. VM/ping-only)
        seen_this_scan.add(mac)

        if mac not in devices_db:
            # Brand new device
            devices_db[mac] = {
                "mac": d["mac"],
                "ip": d["ip"],
                "hostname": d["hostname"],
                "manufacturer": d["manufacturer"],
                "os": d["os"],
                "known": False,
                "alias": "",
                "first_seen": now,
                "last_seen": now,
                "times_seen": 1,
                "online": True,
            }
            new_macs.append(mac)
        else:
            rec = devices_db[mac]
            was_online = rec.get("online", False)

            # Update dynamic fields
            rec["ip"] = d["ip"]
            rec["last_seen"] = now
            rec["times_seen"] = rec.get("times_seen", 0) + 1
            rec["online"] = True

            # Update info only if we got better data
            if d["hostname"]:
                rec["hostname"] = d["hostname"]
            if d["manufacturer"]:
                rec["manufacturer"] = d["manufacturer"]
            if d["os"]:
                rec["os"] = d["os"]

            if not was_online:
                returned_macs.append(mac)

    # Mark offline devices not seen in this scan
    for mac in devices_db:
        if mac not in seen_this_scan:
            devices_db[mac]["online"] = False

    return new_macs, returned_macs


# ── Display ────────────────────────────────────────────────────────────────

def display_device_label(d: dict) -> str:
    """Return alias or hostname or MAC/IP."""
    return d.get("alias") or d.get("hostname") or d.get("mac") or d.get("ip", "?")


def display_devices(devices_db: dict, show_offline: bool = True) -> None:
    table = Table(
        title="Dispositius a la xarxa",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Estat", justify="center", style="bold", no_wrap=True)
    table.add_column("Conegut", justify="center")
    table.add_column("Nom / Àlies", style="cyan")
    table.add_column("IP", style="yellow", no_wrap=True)
    table.add_column("MAC", style="dim", no_wrap=True)
    table.add_column("Fabricant", style="magenta")
    table.add_column("OS", style="blue")
    table.add_column("Vist per última vegada", style="dim")

    for mac, d in sorted(devices_db.items(), key=lambda x: x[1].get("ip", "")):
        online = d.get("online", False)
        if not online and not show_offline:
            continue

        status = "[green]●[/green]" if online else "[red]○[/red]"
        known = "[green]✓[/green]" if d.get("known") else "[red]✗[/red]"
        label = display_device_label(d)
        last = d.get("last_seen", "")[:16].replace("T", " ")

        table.add_row(
            status,
            known,
            label,
            d.get("ip", ""),
            d.get("mac", ""),
            d.get("manufacturer", ""),
            d.get("os", ""),
            last,
        )

    console.print(table)
    total = len(devices_db)
    online = sum(1 for d in devices_db.values() if d.get("online"))
    known = sum(1 for d in devices_db.values() if d.get("known"))
    console.print(
        f"Total: [bold]{total}[/bold] | "
        f"En línia: [green]{online}[/green] | "
        f"Coneguts: [cyan]{known}[/cyan] | "
        f"Desconeguts: [red]{total - known}[/red]"
    )


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_scan(args, cfg: dict) -> None:
    network = args.network or cfg.get("network", "192.168.1.0/24")
    devices_db = load_devices()
    scanned = scan_network(network, aggressive=args.aggressive)
    new_macs, returned_macs = merge_scan_results(devices_db, scanned)
    save_devices(devices_db)

    display_devices(devices_db, show_offline=not args.online_only)

    tg = cfg.get("telegram", {})
    if tg.get("token") and tg.get("chat_id"):
        for mac in new_macs:
            d = devices_db[mac]
            if not d.get("known"):
                msg = build_alert_message(d)
                ok = send_telegram(tg["token"], tg["chat_id"], msg)
                if ok:
                    console.print(f"[green]Alerta Telegram enviada per {mac}[/green]")
                else:
                    console.print(f"[red]Error enviant alerta per {mac}[/red]")


def cmd_list(args, cfg: dict) -> None:
    devices_db = load_devices()
    if not devices_db:
        console.print("[yellow]No hi ha dispositius registrats. Fes primer un scan.[/yellow]")
        return
    display_devices(devices_db, show_offline=not args.online_only)


def cmd_mark(args, cfg: dict) -> None:
    devices_db = load_devices()
    query = args.identifier.upper()
    matched = []

    for mac, d in devices_db.items():
        if (query in mac.upper() or
                query in d.get("ip", "").upper() or
                query in d.get("hostname", "").upper() or
                query in d.get("alias", "").upper()):
            matched.append(mac)

    if not matched:
        console.print(f"[red]No s'ha trobat cap dispositiu amb: {args.identifier}[/red]")
        return

    for mac in matched:
        d = devices_db[mac]
        d["known"] = True
        if args.alias:
            d["alias"] = args.alias
        label = display_device_label(d)
        console.print(f"[green]✓ Marcat com a conegut:[/green] {label} ({mac})")

    save_devices(devices_db)


def cmd_unmark(args, cfg: dict) -> None:
    devices_db = load_devices()
    query = args.identifier.upper()
    matched = []

    for mac, d in devices_db.items():
        if (query in mac.upper() or
                query in d.get("ip", "").upper() or
                query in d.get("hostname", "").upper() or
                query in d.get("alias", "").upper()):
            matched.append(mac)

    if not matched:
        console.print(f"[red]No s'ha trobat cap dispositiu amb: {args.identifier}[/red]")
        return

    for mac in matched:
        devices_db[mac]["known"] = False
        label = display_device_label(devices_db[mac])
        console.print(f"[yellow]✗ Desmarcat:[/yellow] {label} ({mac})")

    save_devices(devices_db)


def cmd_alias(args, cfg: dict) -> None:
    devices_db = load_devices()
    query = args.identifier.upper()
    matched = []

    for mac, d in devices_db.items():
        if (query in mac.upper() or
                query in d.get("ip", "").upper() or
                query in d.get("hostname", "").upper()):
            matched.append(mac)

    if not matched:
        console.print(f"[red]No s'ha trobat cap dispositiu amb: {args.identifier}[/red]")
        return

    for mac in matched:
        devices_db[mac]["alias"] = args.alias
        console.print(f"[cyan]Àlies assignat '{args.alias}' a {mac}[/cyan]")

    save_devices(devices_db)


def cmd_monitor(args, cfg: dict) -> None:
    interval = args.interval or cfg.get("monitor_interval", 60)
    network = args.network or cfg.get("network", "192.168.1.0/24")

    console.print(Panel(
        f"[bold green]Mode monitor actiu[/bold green]\n"
        f"Xarxa: [cyan]{network}[/cyan]\n"
        f"Interval: [yellow]{interval}s[/yellow]\n"
        f"Prem Ctrl+C per aturar.",
        title="WiFi Scanner - Monitor",
    ))

    tg = cfg.get("telegram", {})

    try:
        while True:
            devices_db = load_devices()
            scanned = scan_network(network, aggressive=args.aggressive)
            new_macs, returned_macs = merge_scan_results(devices_db, scanned)
            save_devices(devices_db)

            if new_macs or returned_macs:
                display_devices(devices_db, show_offline=False)

            for mac in new_macs:
                d = devices_db[mac]
                label = display_device_label(d)
                console.print(f"[bold red]NOU dispositiu:[/bold red] {label} — {d.get('ip')} — {d.get('manufacturer', '')}")
                if tg.get("token") and tg.get("chat_id") and not d.get("known"):
                    send_telegram(tg["token"], tg["chat_id"], build_alert_message(d))

            for mac in returned_macs:
                d = devices_db[mac]
                label = display_device_label(d)
                console.print(f"[yellow]Dispositiu reconnectat:[/yellow] {label} — {d.get('ip')}")
                if tg.get("token") and tg.get("chat_id") and not d.get("known"):
                    msg = f"🔄 <b>Dispositiu reconnectat</b>\n"
                    msg += build_alert_message(d).split("\n", 1)[1]
                    send_telegram(tg["token"], tg["chat_id"], msg)

            console.print(f"[dim]Propera exploració en {interval}s... ({datetime.now().strftime('%H:%M:%S')})[/dim]")
            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor aturat.[/yellow]")


def cmd_test_telegram(args, cfg: dict) -> None:
    tg = cfg.get("telegram", {})
    if not tg.get("token") or not tg.get("chat_id"):
        console.print("[red]Falta token o chat_id de Telegram a config.yml[/red]")
        return
    ok = send_telegram(
        tg["token"],
        tg["chat_id"],
        "✅ <b>WiFi Scanner</b> connectat correctament!",
    )
    if ok:
        console.print("[green]Missatge de prova enviat correctament![/green]")
    else:
        console.print("[red]Error enviant missatge. Comprova token i chat_id.[/red]")


def cmd_delete(args, cfg: dict) -> None:
    devices_db = load_devices()
    query = args.identifier.upper()
    matched = [
        mac for mac, d in devices_db.items()
        if (query in mac.upper() or
            query in d.get("ip", "").upper() or
            query in d.get("hostname", "").upper() or
            query in d.get("alias", "").upper())
    ]
    if not matched:
        console.print(f"[red]No s'ha trobat cap dispositiu: {args.identifier}[/red]")
        return
    for mac in matched:
        label = display_device_label(devices_db[mac])
        del devices_db[mac]
        console.print(f"[red]Eliminat:[/red] {label} ({mac})")
    save_devices(devices_db)


# ── CLI setup ──────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Escàner de dispositius WiFi amb alertes Telegram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  sudo python wifi_scanner.py scan
  sudo python wifi_scanner.py scan --network 192.168.0.0/24 --aggressive
  python wifi_scanner.py list
  python wifi_scanner.py list --online-only
  python wifi_scanner.py mark 192.168.1.5 --alias "El meu mòbil"
  python wifi_scanner.py mark AA:BB:CC:DD:EE:FF --alias "Ruter principal"
  python wifi_scanner.py alias AA:BB:CC:DD --alias "Chromecast"
  python wifi_scanner.py unmark AA:BB:CC:DD:EE:FF
  sudo python wifi_scanner.py monitor --interval 30
  python wifi_scanner.py test-telegram
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="Escanejar la xarxa una vegada")
    p_scan.add_argument("--network", "-n", help="Rang de xarxa (p.ex. 192.168.1.0/24)")
    p_scan.add_argument("--aggressive", "-a", action="store_true",
                        help="Activar detecció de SO (necessita root)")
    p_scan.add_argument("--online-only", action="store_true",
                        help="Mostrar només dispositius en línia")

    # list
    p_list = sub.add_parser("list", help="Llistar dispositius registrats")
    p_list.add_argument("--online-only", action="store_true",
                        help="Mostrar només dispositius en línia")

    # mark
    p_mark = sub.add_parser("mark", help="Marcar dispositiu com a conegut")
    p_mark.add_argument("identifier", help="IP, MAC o nom del dispositiu")
    p_mark.add_argument("--alias", "-l", help="Posar un àlies al dispositiu")

    # unmark
    p_unmark = sub.add_parser("unmark", help="Desmarcar dispositiu com a desconegut")
    p_unmark.add_argument("identifier", help="IP, MAC o nom del dispositiu")

    # alias
    p_alias = sub.add_parser("alias", help="Assignar àlies a un dispositiu")
    p_alias.add_argument("identifier", help="IP, MAC o nom del dispositiu")
    p_alias.add_argument("alias", help="Nom a assignar")

    # monitor
    p_mon = sub.add_parser("monitor", help="Monitorització contínua amb alertes Telegram")
    p_mon.add_argument("--network", "-n", help="Rang de xarxa (p.ex. 192.168.1.0/24)")
    p_mon.add_argument("--interval", "-i", type=int, help="Interval entre escanejos (segons)")
    p_mon.add_argument("--aggressive", "-a", action="store_true",
                       help="Activar detecció de SO (necessita root)")

    # test-telegram
    sub.add_parser("test-telegram", help="Provar la connexió Telegram")

    # delete
    p_del = sub.add_parser("delete", help="Eliminar dispositiu de la base de dades")
    p_del.add_argument("identifier", help="IP, MAC o nom del dispositiu")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config()

    dispatch = {
        "scan": cmd_scan,
        "list": cmd_list,
        "mark": cmd_mark,
        "unmark": cmd_unmark,
        "alias": cmd_alias,
        "monitor": cmd_monitor,
        "test-telegram": cmd_test_telegram,
        "delete": cmd_delete,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args, cfg)


if __name__ == "__main__":
    main()
