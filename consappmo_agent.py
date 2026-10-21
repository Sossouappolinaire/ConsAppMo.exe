#!/usr/bin/env python3
"""Agent ConsAppMo : lit les vrais compteurs réseau du PC et les donne à ConsAppMo.html.

Installation (une seule fois) :  pip install psutil
Lancement :                      python consappmo_agent.py
Puis ouvrez http://127.0.0.1:8765 dans votre navigateur.
Gardez ce fichier et ConsAppMo.html dans le même dossier.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import psutil
except ImportError:
    sys.exit("psutil est manquant. Installez-le avec :  pip install psutil")

PORT = 8765
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WIFI = ("wi-fi", "wifi", "wlan", "wlp", "wlx", "wireless", "sans fil", "airport")
SKIP = ("loopback", "vethernet", "docker", "veth", "br-", "isatap", "teredo")


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3,
                              errors="ignore").stdout
    except Exception:
        return ""


def ssid():
    """Nom du réseau Wi-Fi auquel le PC est connecté (vide si introuvable)."""
    if sys.platform.startswith("win"):
        m = re.search(r"^\s*SSID\s*:\s*(.+)$", run(["netsh", "wlan", "show", "interfaces"]), re.M)
    elif sys.platform == "darwin":
        out = run(["networksetup", "-getairportnetwork", "en0"])
        m = re.search(r":\s*(.+)$", out) if "Network:" in out else None
    else:
        m = re.search(r"^yes:(.+)$", run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"]), re.M)
    return m.group(1).strip() if m else ""


def is_wifi(name):
    return name.lower().startswith(WIFI) or any(w in name.lower() for w in WIFI)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/stats"):
            ifaces = {}
            for name, c in psutil.net_io_counters(pernic=True).items():
                low = name.lower()
                if low == "lo" or low.startswith(SKIP):
                    continue
                ifaces[name] = {"rx": c.bytes_recv, "tx": c.bytes_sent}
            up = psutil.net_if_stats()
            wifi = [n for n in ifaces if is_wifi(n) and up.get(n) and up[n].isup]
            body = json.dumps({"t": time.time(), "ifaces": ifaces,
                               "wifi": wifi[0] if wifi else "", "ssid": ssid() if wifi else ""}).encode()
            self.reply(200, body, "application/json")
            return
        try:
            with open(os.path.join(HERE, "ConsAppMo.html"), "rb") as f:
                self.reply(200, f.read(), "text/html; charset=utf-8")
        except OSError:
            msg = "Placez ConsAppMo.html dans le même dossier que ce script."
            self.reply(404, msg.encode(), "text/plain; charset=utf-8")


url = "http://127.0.0.1:%d" % PORT
try:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
except OSError:
    print("Le port %d est déjà utilisé : ConsAppMo tourne peut-être déjà." % PORT)
    webbrowser.open(url)
    input("Appuyez sur Entrée pour fermer.")
    sys.exit(1)
print("ConsAppMo est lancé : %s (fermez cette fenêtre pour arrêter)" % url)
threading.Timer(1, webbrowser.open, [url]).start()
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
