#!/usr/bin/env python3
"""Ingress-Weboberfläche und Zeitplan für das HA-Doku-Add-on (nur Standardbibliothek + ha_doc)."""
import calendar
import datetime as dt
import html
import json
import os
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

import ha_doc

OUT_DIR = os.environ.get("HA_DOC_OUT", "/share/ha_doc")
DATA_DIR = os.environ.get("HA_DOC_DATA", "/data")
DEMO = os.environ.get("HA_DOC_DEMO") == "1"
PORT = int(os.environ.get("HA_DOC_PORT", "8099"))
SUPERVISOR_IP = "172.30.32.2"  # Ingress-Anfragen kommen nur von hier
os.makedirs(OUT_DIR, exist_ok=True)


def load_options():
    path = os.environ.get("HA_DOC_OPTIONS", os.path.join(DATA_DIR, "options.json"))
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


OPTIONS = load_options()
ALL_SECTIONS = [k for k, _ in ha_doc.SECTIONS]
state = {"running": False, "msg": "", "error": "", "sections": list(ALL_SECTIONS), "areas": None,
         "hide_diag": False, "only_problems": False}
lock = threading.Lock()
_areas_cache = {"t": 0.0, "v": []}
_tz_cache = {}


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def sup_get(path):
    import requests
    r = requests.get("http://supervisor/core" + path, headers={"Authorization": "Bearer " + os.environ["SUPERVISOR_TOKEN"]}, timeout=20)
    return r.json() if r.status_code == 200 else None


def get_tz():
    if "tz" not in _tz_cache:
        name = "UTC"
        try:
            if not DEMO:
                name = (sup_get("/api/config") or {}).get("time_zone") or "UTC"
            from zoneinfo import ZoneInfo
            _tz_cache["tz"] = ZoneInfo(name)
        except Exception:
            _tz_cache["tz"] = dt.timezone.utc
    return _tz_cache["tz"]


def get_areas():
    """Liste (area_id, Name) für die Bereichsauswahl, 2 Minuten zwischengespeichert."""
    if time.time() - _areas_cache["t"] < 120 and _areas_cache["v"]:
        return _areas_cache["v"]
    try:
        if DEMO:
            raw = ha_doc.demo_data()["areas"]
        else:
            c = ha_doc.HAClient(None, os.environ["SUPERVISOR_TOKEN"], supervisor=True)
            raw = c.ws_call("config/area_registry/list") or []
            c.ws.close()
        _areas_cache["v"] = sorted(((a["area_id"], a["name"]) for a in raw), key=lambda x: x[1].lower())
        _areas_cache["t"] = time.time()
    except Exception:
        traceback.print_exc()
    return _areas_cache["v"]


def cleanup_old():
    keep = int(OPTIONS.get("keep_last", 12) or 12)
    files = sorted(f for f in os.listdir(OUT_DIR) if f.startswith("ha_dokumentation_") and f.endswith(".pdf"))
    for f in files[:-keep] if len(files) > keep else []:
        try:
            os.remove(os.path.join(OUT_DIR, f))
        except OSError:
            pass


def generate(sections, options, source="manuell"):
    try:
        state.update(msg="Lese Daten aus Home Assistant …", error="")
        data = ha_doc.demo_data() if DEMO else ha_doc.fetch_all(None, os.environ["SUPERVISOR_TOKEN"], supervisor=True)
        state["msg"] = "Erstelle PDF …"
        name = dt.datetime.now().strftime("ha_dokumentation_%Y%m%d_%H%M%S.pdf")
        ha_doc.build_pdf(data, os.path.join(OUT_DIR, name), sections=sections, options=options)
        cleanup_old()
        state["msg"] = f"Fertig ({source}): {name}"
    except Exception:
        state["error"] = traceback.format_exc()
        state["msg"] = "Fehler beim Erstellen"
    finally:
        state["running"] = False


def start_generation(sections, options, source="manuell"):
    with lock:
        if state["running"]:
            return False
        state["running"] = True
        state["msg"] = "Starte …"
    threading.Thread(target=generate, args=(sections, options, source), daemon=True).start()
    return True


# --------------------------------------------------------------------------
# Monatlicher Bericht
# --------------------------------------------------------------------------

SCHED_FILE = os.path.join(DATA_DIR, "scheduler.json")


def last_run():
    try:
        with open(SCHED_FILE, encoding="utf-8") as f:
            return json.load(f).get("last", "")
    except Exception:
        return ""


def mark_run(key):
    try:
        with open(SCHED_FILE, "w", encoding="utf-8") as f:
            json.dump({"last": key}, f)
    except Exception:
        traceback.print_exc()


def scheduled_settings():
    """Abschnitte und Filter für den Monatsbericht aus der Add-on-Konfiguration."""
    sections = [k for k in ALL_SECTIONS if OPTIONS.get(f"schedule_{k}", True)] or list(ALL_SECTIONS)
    wanted = [str(x).strip().lower() for x in (OPTIONS.get("schedule_areas") or []) if str(x).strip()]
    areas = None
    if wanted:
        areas = [aid for aid, name in get_areas() if aid.lower() in wanted or name.lower() in wanted]
        if "_none" in wanted or "ohne bereich" in wanted:
            areas.append("_none")
    return sections, {"hide_diagnostic": bool(OPTIONS.get("schedule_hide_diagnostic", True)),
                      "only_problems": bool(OPTIONS.get("schedule_only_problems", False)), "areas": areas}


def scheduler_loop():
    while True:
        try:
            if OPTIONS.get("schedule_enabled"):
                now = dt.datetime.now(get_tz())
                day = min(int(OPTIONS.get("schedule_day", 1)), calendar.monthrange(now.year, now.month)[1])
                hhmm = str(OPTIONS.get("schedule_time", "03:00"))
                key = now.strftime("%Y-%m")
                if now.day == day and now.strftime("%H:%M") >= hhmm and last_run() != key:
                    sections, opts = scheduled_settings()
                    if start_generation(sections, opts, source="automatisch"):
                        mark_run(key)
        except Exception:
            traceback.print_exc()
        time.sleep(30)


def schedule_info():
    if not OPTIONS.get("schedule_enabled"):
        return "Automatischer Monatsbericht: aus (einschalten unter Konfiguration des Add-ons)."
    last = last_run()
    sections, o = scheduled_settings()
    labels = dict(ha_doc.SECTIONS)
    inhalt = "alle Abschnitte" if len(sections) == len(ALL_SECTIONS) else ", ".join(labels[x] for x in sections)
    filt = [x for x, on in (("ohne Diagnose-Entitäten", o["hide_diagnostic"]), ("nur fehlende Entitäten", o["only_problems"]),
                            ("ausgewählte Bereiche", o["areas"] is not None)) if on]
    return (f"Automatischer Monatsbericht: jeden Monat am {OPTIONS.get('schedule_day', 1)}. um {OPTIONS.get('schedule_time', '03:00')} Uhr "
            f"({inhalt}" + (f"; {', '.join(filt)}" if filt else "") + f"), letzte {OPTIONS.get('keep_last', 12)} PDFs werden behalten"
            + (f", zuletzt: {last}." if last else "."))


# --------------------------------------------------------------------------
# Weboberfläche
# --------------------------------------------------------------------------

def checkbox(name, value, label, checked):
    return f'<label class="opt"><input type="checkbox" name="{name}" value="{html.escape(value)}"{" checked" if checked else ""}> {html.escape(label)}</label>'


def page():
    files = sorted((f for f in os.listdir(OUT_DIR) if f.endswith(".pdf")), reverse=True)
    rows = "".join(
        f'<tr><td><a href="files/{html.escape(f)}" target="_blank">{html.escape(f)}</a></td>'
        f'<td>{os.path.getsize(os.path.join(OUT_DIR, f)) // 1024} KB</td></tr>' for f in files
    ) or '<tr><td colspan="2">Noch keine PDFs erstellt.</td></tr>'
    refresh = '<meta http-equiv="refresh" content="2">' if state["running"] else ""
    btn = "disabled" if state["running"] else ""
    err = f'<pre class="err">{html.escape(state["error"])}</pre>' if state["error"] else ""
    boxes = "".join(checkbox("sections", k, label, k in state["sections"]) for k, label in ha_doc.SECTIONS)
    areas = get_areas()
    area_html = ""
    if areas:
        sel = state["areas"]
        items = "".join(checkbox("areas", aid, name, sel is None or aid in sel) for aid, name in areas)
        items += checkbox("areas", "_none", "Ohne Bereich", sel is None or "_none" in sel)
        area_html = (f'<details><summary>Bereiche auswählen ({len(areas) + 1})</summary><input type="hidden" name="areas_present" value="1">'
                     f'<div class="opts">{items}</div></details>')
    extra = (checkbox("hide_diag", "1", "Konfigurations- und Diagnose-Entitäten ausblenden (kürzere Geräteliste)", state["hide_diag"]) +
             checkbox("only_problems", "1", "Automatisierungen, Skripte, Szenen: nur mit fehlenden Entitäten", state["only_problems"]))
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">{refresh}
<meta name="viewport" content="width=device-width,initial-scale=1"><title>HA Doku</title>
<style>
:root{{--bg:#fafbfc;--fg:#1f2933;--card:#fff;--line:#e1e5e9;--muted:#52606d;--accent:#03a9f4;--link:#0277bd;--errbg:#fdecea;color-scheme:light}}
@media (prefers-color-scheme: dark){{:root{{--bg:#1c1c1c;--fg:#e1e1e1;--card:#2a2a2a;--line:#3c3c3c;--muted:#a8a8a8;--link:#4fc3f7;--errbg:#4a2626;color-scheme:dark}}}}
body{{font-family:system-ui,sans-serif;margin:0;padding:24px;max-width:820px;color:var(--fg);background:var(--bg)}}
h1{{margin-top:0}} h2{{font-size:15px;margin:18px 0 6px;color:var(--muted)}}
button{{background:var(--accent);color:#fff;border:0;padding:12px 22px;border-radius:8px;font-size:16px;cursor:pointer}}
button[disabled]{{opacity:.5;cursor:wait}} table{{border-collapse:collapse;width:100%;margin-top:18px;background:var(--card)}}
td,th{{border:1px solid var(--line);padding:8px 10px;text-align:left}} .msg{{margin:14px 0;color:var(--muted)}}
.opts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px;margin:8px 0}}
.opt{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;cursor:pointer;display:block}}
details{{margin:10px 0}} summary{{cursor:pointer;color:var(--link)}} a{{color:var(--link)}}
.err{{background:var(--errbg);padding:10px;overflow:auto;font-size:12px}}
</style>
<script>
try{{const cs=getComputedStyle(window.parent.document.documentElement);
const m={{'--bg':'--primary-background-color','--fg':'--primary-text-color','--card':'--card-background-color','--line':'--divider-color','--muted':'--secondary-text-color','--accent':'--primary-color'}};
for(const k in m){{const v=cs.getPropertyValue(m[k]).trim();if(v)document.documentElement.style.setProperty(k,v);}}
const c=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
const t=document.createElement('canvas').getContext('2d');t.fillStyle=c;t.fillRect(0,0,1,1);const d=t.getImageData(0,0,1,1).data;
document.documentElement.style.colorScheme=(0.299*d[0]+0.587*d[1]+0.114*d[2])<128?'dark':'light';}}catch(e){{}}
</script></head><body>
<h1>Home Assistant Dokumentation</h1>
<p>Erstellt ein PDF deiner Installation. Wähle, was enthalten sein soll.</p>
<form method="post" action="generate">
<h2>Abschnitte</h2><div class="opts">{boxes}</div>
<h2>Optionen</h2><div class="opts" style="grid-template-columns:1fr">{extra}</div>
{area_html}
<p><button {btn}>PDF erstellen</button></p></form>
<div class="msg">{html.escape(state["msg"])}</div>{err}
<table><tr><th>Datei</th><th>Grösse</th></tr>{rows}</table>
<p class="msg">{html.escape(schedule_info())}<br>Ablage: Freigabe «share» → Ordner ha_doc</p>
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
        sections = [x for x in form.get("sections", []) if x in ALL_SECTIONS]
        area_ids = {a for a, _ in get_areas()} | {"_none"}
        areas = [x for x in form.get("areas", []) if x in area_ids] if "areas_present" in form else None
        opts = {"hide_diagnostic": "hide_diag" in form, "only_problems": "only_problems" in form, "areas": areas}
        if not sections:
            state["msg"] = "Bitte mindestens einen Abschnitt auswählen."
        else:
            state.update(sections=sections, areas=areas, hide_diag=opts["hide_diagnostic"], only_problems=opts["only_problems"])
            start_generation(sections, opts)
        self._send(303, "", extra={"Location": "./"})

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    print(f"HA-Doku-Server auf Port {PORT}", flush=True)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
