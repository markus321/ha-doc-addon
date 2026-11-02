#!/usr/bin/env python3
"""Ingress-Weboberflaeche fuer das HA-Doku-Add-on (nur Standardbibliothek)."""
import datetime as dt
import html
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

import ha_doc

OUT_DIR = os.environ.get("HA_DOC_OUT", "/share/ha_doc")
DEMO = os.environ.get("HA_DOC_DEMO") == "1"
PORT = int(os.environ.get("HA_DOC_PORT", "8099"))
SUPERVISOR_IP = "172.30.32.2"  # Ingress-Anfragen kommen nur von hier
os.makedirs(OUT_DIR, exist_ok=True)

state = {"running": False, "msg": "", "error": "", "sections": [k for k, _ in ha_doc.SECTIONS]}
lock = threading.Lock()


def generate(sections):
    try:
        state.update(msg="Lese Daten aus Home Assistant …", error="")
        data = ha_doc.demo_data() if DEMO else ha_doc.fetch_all(None, os.environ["SUPERVISOR_TOKEN"], supervisor=True)
        state["msg"] = "Erstelle PDF …"
        name = dt.datetime.now().strftime("ha_dokumentation_%Y%m%d_%H%M%S.pdf")
        ha_doc.build_pdf(data, os.path.join(OUT_DIR, name), sections=sections)
        state["msg"] = f"Fertig: {name}"
    except Exception:
        state["error"] = traceback.format_exc()
        state["msg"] = "Fehler beim Erstellen"
    finally:
        state["running"] = False


def page():
    files = sorted((f for f in os.listdir(OUT_DIR) if f.endswith(".pdf")), reverse=True)
    rows = "".join(
        f'<tr><td><a href="files/{html.escape(f)}" target="_blank">{html.escape(f)}</a></td>'
        f'<td>{os.path.getsize(os.path.join(OUT_DIR, f)) // 1024} KB</td></tr>' for f in files
    ) or '<tr><td colspan="2">Noch keine PDFs erstellt.</td></tr>'
    refresh = '<meta http-equiv="refresh" content="2">' if state["running"] else ""
    btn = "disabled" if state["running"] else ""
    boxes = "".join(
        f'<label class="opt"><input type="checkbox" name="sections" value="{k}"{" checked" if k in state["sections"] else ""}> {html.escape(label)}</label>'
        for k, label in ha_doc.SECTIONS)
    err = f'<pre class="err">{html.escape(state["error"])}</pre>' if state["error"] else ""
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">{refresh}
<meta name="viewport" content="width=device-width,initial-scale=1"><title>HA Doku</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;padding:24px;max-width:760px;color:#1f2933;background:#fafbfc}}
h1{{margin-top:0}} button{{background:#03a9f4;color:#fff;border:0;padding:12px 22px;border-radius:8px;font-size:16px;cursor:pointer}}
button[disabled]{{background:#9bbccc;cursor:wait}} table{{border-collapse:collapse;width:100%;margin-top:18px;background:#fff}}
td,th{{border:1px solid #e1e5e9;padding:8px 10px;text-align:left}} .msg{{margin:14px 0;color:#52606d}}
.opts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:6px;margin:12px 0 18px}}
.opt{{background:#fff;border:1px solid #e1e5e9;border-radius:8px;padding:8px 10px;cursor:pointer}}
.err{{background:#fdecea;padding:10px;overflow:auto;font-size:12px}}
</style></head><body>
<h1>Home Assistant Dokumentation</h1>
<p>Erstellt ein PDF mit Bereichen, Geräten, Automatisierungen, Skripten, Szenen und Auffälligkeiten.</p>
<form method="post" action="generate"><div class="opts">{boxes}</div><button {btn}>PDF erstellen</button></form>
<div class="msg">{html.escape(state["msg"])}</div>{err}
<table><tr><th>Datei</th><th>Grösse</th></tr>{rows}</table>
<p class="msg">Ablage: Freigabe «share» → Ordner ha_doc</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _allowed(self):
        if DEMO:
            return True
        if self.client_address[0] != SUPERVISOR_IP:
            self.send_error(403)
            return False
        return True

    def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        body = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._allowed():
            return
        path = self.path.split("?")[0]
        if "/files/" in path:
            name = os.path.basename(unquote(path.split("/files/", 1)[1]))
            full = os.path.join(OUT_DIR, name)
            if name.endswith(".pdf") and os.path.isfile(full):
                with open(full, "rb") as f:
                    return self._send(200, f.read(), "application/pdf", {"Content-Disposition": f'inline; filename="{name}"'})
            return self.send_error(404)
        self._send(200, page())

    def do_POST(self):
        if not self._allowed():
            return
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        valid = {k for k, _ in ha_doc.SECTIONS}
        sections = [x for x in form.get("sections", []) if x in valid]
        with lock:
            if not sections:
                state["msg"] = "Bitte mindestens einen Abschnitt auswählen."
            elif not state["running"]:
                state["running"] = True
                state["sections"] = sections
                state["msg"] = "Starte …"
                threading.Thread(target=generate, args=(sections,), daemon=True).start()
        self._send(303, "", extra={"Location": "./"})

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    print(f"HA-Doku-Server auf Port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
