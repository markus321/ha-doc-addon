#!/usr/bin/env python3
"""
ha_doc - Home Assistant Dokumentation als PDF (Prototyp)

Verwendung:
    python ha_doc.py --url http://homeassistant.local:8123 --token <LONG_LIVED_TOKEN> -o ha_doku.pdf
    python ha_doc.py --demo -o demo.pdf          # ohne HA, mit Beispieldaten

Abhaengigkeiten:  pip install reportlab requests websocket-client
Token erstellen:  HA-Profil -> Sicherheit -> Langlebige Zugriffstoken
"""
import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from xml.sax.saxutils import escape

# --------------------------------------------------------------------------
# 1. Daten holen
# --------------------------------------------------------------------------


class HAClient:
    def __init__(self, url, token, supervisor=False):
        import requests
        import websocket

        # Im Add-on laeuft alles ueber den Supervisor-Proxy
        self.base = "http://supervisor/core" if supervisor else url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.requests = requests
        ws_path = "/websocket" if supervisor else "/api/websocket"
        ws_url = self.base.replace("https://", "wss://").replace("http://", "ws://") + ws_path
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.ws.recv()  # auth_required
        self.ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(self.ws.recv()).get("type") != "auth_ok":
            raise SystemExit("Authentifizierung fehlgeschlagen (Token pruefen).")
        self._id = 0

    def ws_call(self, msg_type, **kw):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "type": msg_type, **kw}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if not msg.get("success", True):
                    return []
                return msg.get("result")

    def get(self, path):
        r = self.requests.get(self.base + path, headers=self.headers, timeout=30)
        if r.status_code != 200:
            return None
        return r.json()


def fetch_all(url, token, supervisor=False):
    c = HAClient(url, token, supervisor)
    data = {
        "config": c.get("/api/config") or {},
        "states": c.ws_call("get_states") or [],
        "entities": c.ws_call("config/entity_registry/list") or [],
        "devices": c.ws_call("config/device_registry/list") or [],
        "areas": c.ws_call("config/area_registry/list") or [],
        "floors": c.ws_call("config/floor_registry/list") or [],
        "entries": c.ws_call("config_entries/get") or [],
        "automations": [],
        "scripts": [],
        "scenes": [],
    }
    for st in data["states"]:
        eid = st["entity_id"]
        dom, obj = eid.split(".", 1)
        attrs = st.get("attributes", {})
        if dom == "automation":
            cfg = c.get(f"/api/config/automation/config/{attrs['id']}") if attrs.get("id") else None
            data["automations"].append({"entity_id": eid, "state": st["state"], "attrs": attrs, "config": cfg})
        elif dom == "script":
            cfg = c.get(f"/api/config/script/config/{obj}")
            data["scripts"].append({"entity_id": eid, "state": st["state"], "attrs": attrs, "config": cfg})
        elif dom == "scene":
            cfg = c.get(f"/api/config/scene/config/{attrs['id']}") if attrs.get("id") else None
            data["scenes"].append({"entity_id": eid, "state": st["state"], "attrs": attrs, "config": cfg})
    return data


def demo_data():
    now = dt.datetime.now().isoformat()
    st = lambda eid, s="on", **a: {"entity_id": eid, "state": s, "attributes": a, "last_changed": now}
    states = [
        st("light.wohnzimmer_decke", friendly_name="Wohnzimmer Decke"),
        st("light.kueche_spots", friendly_name="Küche Spots"),
        st("cover.wohnzimmer_storen", "open", friendly_name="Wohnzimmer Storen"),
        st("binary_sensor.bewegung_flur", "off", friendly_name="Bewegung Flur", device_class="motion"),
        st("sensor.temp_wohnzimmer", "21.4", friendly_name="Temperatur Wohnzimmer", unit_of_measurement="°C"),
        st("sensor.alter_sensor", "unavailable", friendly_name="Alter Sensor"),
        st("input_boolean.gaeste_modus", "off", friendly_name="Gäste-Modus"),
        st("input_number.heizung_soll", "21", friendly_name="Heizung Soll", min=15, max=25, unit_of_measurement="°C"),
        st("timer.waschmaschine", "idle", friendly_name="Timer Waschmaschine"),
        st("person.markus", "home", friendly_name="Markus"),
        st("scene.nacht", "unknown", friendly_name="Nacht"),
    ]
    return {
        "config": {"location_name": "Zuhause", "version": "2026.10.3", "time_zone": "Europe/Zurich",
                   "unit_system": {"temperature": "°C"}, "latitude": 46.9, "longitude": 7.4, "elevation": 540},
        "states": states,
        "floors": [{"floor_id": "eg", "name": "Erdgeschoss", "level": 0}, {"floor_id": "og", "name": "Obergeschoss", "level": 1}],
        "areas": [{"area_id": "wohnzimmer", "name": "Wohnzimmer", "floor_id": "eg"},
                  {"area_id": "kueche", "name": "Küche", "floor_id": "eg"},
                  {"area_id": "flur", "name": "Flur", "floor_id": "og"}],
        "devices": [
            {"id": "d1", "name": "IKEA Deckenleuchte", "name_by_user": None, "manufacturer": "IKEA", "model": "TRADFRI Driver", "area_id": "wohnzimmer", "sw_version": "2.3.086"},
            {"id": "d2", "name": "Somfy Storen", "name_by_user": "Storen Wohnzimmer", "manufacturer": "Somfy", "model": "Sonesse 30", "area_id": "wohnzimmer", "sw_version": "1.0"},
            {"id": "d3", "name": "Aqara Bewegung", "name_by_user": None, "manufacturer": "Aqara", "model": "RTCGQ11LM", "area_id": "flur", "sw_version": "3"},
            {"id": "d4", "name": "Hue Spots", "name_by_user": None, "manufacturer": "Signify", "model": "LCG002", "area_id": "kueche", "sw_version": "1.88"},
        ],
        "entities": [
            {"entity_id": "light.wohnzimmer_decke", "device_id": "d1", "area_id": None, "platform": "zha", "disabled_by": None},
            {"entity_id": "cover.wohnzimmer_storen", "device_id": "d2", "area_id": None, "platform": "somfy_mylink", "disabled_by": None},
            {"entity_id": "binary_sensor.bewegung_flur", "device_id": "d3", "area_id": None, "platform": "zha", "disabled_by": None},
            {"entity_id": "light.kueche_spots", "device_id": "d4", "area_id": None, "platform": "hue", "disabled_by": None},
            {"entity_id": "sensor.alter_sensor", "device_id": None, "area_id": None, "platform": "mqtt", "disabled_by": None},
        ],
        "entries": [
            {"domain": "zha", "title": "Zigbee (ZHA)", "state": "loaded", "source": "user"},
            {"domain": "hue", "title": "Philips Hue", "state": "loaded", "source": "zeroconf"},
            {"domain": "mqtt", "title": "MQTT", "state": "loaded", "source": "user"},
            {"domain": "met", "title": "Wetter", "state": "loaded", "source": "onboarding"},
        ],
        "automations": [
            {"entity_id": "automation.flur_licht", "state": "on",
             "attrs": {"friendly_name": "Flur Licht bei Bewegung", "last_triggered": now, "mode": "restart"},
             "config": {"alias": "Flur Licht bei Bewegung", "description": "Licht im Flur schaltet sich bei Bewegung ein.", "mode": "restart",
                        "triggers": [{"trigger": "state", "entity_id": "binary_sensor.bewegung_flur", "to": "on"}],
                        "conditions": [{"condition": "sun", "after": "sunset", "after_offset": "-00:30:00"},
                                       {"condition": "state", "entity_id": "input_boolean.gaeste_modus", "state": "off"}],
                        "actions": [{"action": "light.turn_on", "target": {"entity_id": "light.wohnzimmer_decke"}, "data": {"brightness_pct": 40}},
                                    {"wait_for_trigger": [{"trigger": "state", "entity_id": "binary_sensor.bewegung_flur", "to": "off", "for": "00:02:00"}]},
                                    {"action": "light.turn_off", "target": {"entity_id": "light.wohnzimmer_decke"}}]}},
            {"entity_id": "automation.storen_hitze", "state": "on",
             "attrs": {"friendly_name": "Storen bei Hitze schliessen", "last_triggered": None},
             "config": {"alias": "Storen bei Hitze schliessen", "mode": "single",
                        "triggers": [{"trigger": "numeric_state", "entity_id": "sensor.temp_wohnzimmer", "above": 25},
                                     {"trigger": "time", "at": "13:00:00"}],
                        "conditions": [{"condition": "or", "conditions": [
                            {"condition": "time", "weekday": ["mon", "tue", "wed", "thu", "fri"]},
                            {"condition": "state", "entity_id": "person.markus", "state": "home"}]}],
                        "actions": [{"if": [{"condition": "state", "entity_id": "cover.wohnzimmer_storen", "state": "open"}],
                                     "then": [{"action": "cover.set_cover_position", "target": {"entity_id": "cover.wohnzimmer_storen"}, "data": {"position": 20}}],
                                     "else": [{"stop": "Bereits geschlossen"}]}]}},
            {"entity_id": "automation.nachts", "state": "off",
             "attrs": {"friendly_name": "Gute Nacht", "last_triggered": None},
             "config": {"alias": "Gute Nacht", "mode": "single",
                        "triggers": [{"trigger": "time", "at": "22:30:00"}],
                        "actions": [{"action": "scene.turn_on", "target": {"entity_id": "scene.nacht"}},
                                    {"choose": [{"conditions": [{"condition": "state", "entity_id": "person.markus", "state": "home"}],
                                                 "sequence": [{"action": "notify.mobile_app_markus", "data": {"message": "Gute Nacht!"}}]}],
                                     "default": []}]}},
        ],
        "scripts": [
            {"entity_id": "script.alles_aus", "state": "off", "attrs": {"friendly_name": "Alles aus"},
             "config": {"alias": "Alles aus", "description": "Schaltet alle Lichter aus.", "mode": "single",
                        "sequence": [{"action": "light.turn_off", "target": {"entity_id": "all"}},
                                     {"delay": {"minutes": 1}},
                                     {"action": "cover.close_cover", "target": {"area_id": "wohnzimmer"}}]}},
        ],
        "scenes": [
            {"entity_id": "scene.nacht", "state": "unknown", "attrs": {"friendly_name": "Nacht"},
             "config": {"name": "Nacht", "entities": {"light.wohnzimmer_decke": {"state": "off"}, "light.kueche_spots": {"state": "off"}}}},
        ],
    }


# --------------------------------------------------------------------------
# 2. Klartext-Beschreibung
# --------------------------------------------------------------------------

WEEKDAYS = {"mon": "Mo", "tue": "Di", "wed": "Mi", "thu": "Do", "fri": "Fr", "sat": "Sa", "sun": "So"}


class Namer:
    def __init__(self, data):
        self.names = {}
        for s in data["states"]:
            self.names[s["entity_id"]] = s.get("attributes", {}).get("friendly_name") or s["entity_id"]
        self.areas = {a["area_id"]: a["name"] for a in data["areas"]}

    def ent(self, v):
        if v is None:
            return "?"
        if isinstance(v, list):
            return ", ".join(self.ent(x) for x in v)
        if v == "all":
            return "alle Entitäten"
        n = self.names.get(v)
        return f"{n} [{v}]" if n and n != v else str(v)

    def target(self, t):
        if not isinstance(t, dict):
            return ""
        parts = []
        if t.get("entity_id"):
            parts.append(self.ent(t["entity_id"]))
        if t.get("area_id"):
            ids = t["area_id"] if isinstance(t["area_id"], list) else [t["area_id"]]
            parts.append("Bereich " + ", ".join(self.areas.get(i, i) for i in ids))
        if t.get("device_id"):
            parts.append("Gerät " + (", ".join(t["device_id"]) if isinstance(t["device_id"], list) else t["device_id"]))
        return "; ".join(parts)


def dur(v):
    if isinstance(v, dict):
        units = {"hours": "h", "minutes": "min", "seconds": "s", "milliseconds": "ms", "days": "d"}
        return " ".join(f"{v[k]} {u}" for k, u in units.items() if v.get(k))
    return str(v)


def fmt_data(d):
    if not d:
        return ""
    return ", ".join(f"{k}={json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}" for k, v in d.items())


def describe_trigger(t, n):
    p = t.get("trigger") or t.get("platform") or "?"
    if p == "state":
        s = f"Wenn {n.ent(t.get('entity_id'))} wechselt"
        if t.get("from") is not None:
            s += f" von «{t['from']}»"
        if t.get("to") is not None:
            s += f" auf «{t['to']}»"
        if t.get("for"):
            s += f" für {dur(t['for'])}"
        return s
    if p == "numeric_state":
        s = f"Wenn {n.ent(t.get('entity_id'))}"
        if t.get("above") is not None:
            s += f" über {t['above']}"
        if t.get("below") is not None:
            s += f" unter {t['below']}"
        return s + " steigt/fällt"
    if p == "time":
        return f"Um {t.get('at')} Uhr"
    if p == "time_pattern":
        return "Zeitmuster: " + ", ".join(f"{k}={v}" for k, v in t.items() if k in ("hours", "minutes", "seconds"))
    if p == "sun":
        off = f" (Versatz {t['offset']})" if t.get("offset") else ""
        return f"Bei {'Sonnenaufgang' if t.get('event') == 'sunrise' else 'Sonnenuntergang'}{off}"
    if p == "event":
        return f"Bei Ereignis «{t.get('event_type')}»"
    if p == "homeassistant":
        return f"Beim {'Start' if t.get('event') == 'start' else 'Herunterfahren'} von Home Assistant"
    if p == "zone":
        return f"Wenn {n.ent(t.get('entity_id'))} Zone {t.get('zone')} {'betritt' if t.get('event') == 'enter' else 'verlässt'}"
    if p == "template":
        return f"Wenn Template wahr wird: {t.get('value_template')}"
    if p == "webhook":
        return f"Bei Webhook «{t.get('webhook_id')}»"
    if p == "mqtt":
        return f"Bei MQTT-Nachricht auf «{t.get('topic')}»"
    if p == "device":
        return f"Gerätetrigger: {t.get('type')} ({t.get('subtype', '')})".strip()
    if p == "calendar":
        return f"Kalender {n.ent(t.get('entity_id'))}: {t.get('event')}"
    return f"Trigger «{p}»: " + fmt_data({k: v for k, v in t.items() if k not in ("trigger", "platform", "id", "alias")})


def describe_condition(c, n, indent=0):
    if isinstance(c, str):
        return [("  " * indent) + f"Template: {c}"]
    k = c.get("condition", "?")
    pad = "  " * indent
    if k == "state":
        return [pad + f"{n.ent(c.get('entity_id'))} ist «{c.get('state')}»"]
    if k == "numeric_state":
        s = f"{n.ent(c.get('entity_id'))}"
        if c.get("above") is not None:
            s += f" > {c['above']}"
        if c.get("below") is not None:
            s += f" < {c['below']}"
        return [pad + s]
    if k == "time":
        parts = []
        if c.get("after"):
            parts.append(f"nach {c['after']}")
        if c.get("before"):
            parts.append(f"vor {c['before']}")
        if c.get("weekday"):
            parts.append("an " + "/".join(WEEKDAYS.get(w, w) for w in c["weekday"]))
        return [pad + "Zeit: " + ", ".join(parts)]
    if k == "sun":
        parts = []
        for key, word in (("after", "nach"), ("before", "vor")):
            if c.get(key):
                off = c.get(f"{key}_offset")
                parts.append(f"{word} {'Sonnenaufgang' if c[key] == 'sunrise' else 'Sonnenuntergang'}" + (f" ({off})" if off else ""))
        return [pad + "Sonne: " + ", ".join(parts)]
    if k == "template":
        return [pad + f"Template: {c.get('value_template')}"]
    if k == "zone":
        return [pad + f"{n.ent(c.get('entity_id'))} ist in Zone {c.get('zone')}"]
    if k == "trigger":
        return [pad + f"Ausgelöst durch Trigger-ID {c.get('id')}"]
    if k in ("and", "or", "not"):
        label = {"and": "ALLE davon", "or": "EINE davon", "not": "KEINE davon"}[k]
        out = [pad + label + ":"]
        for sub in c.get("conditions", []):
            out += describe_condition(sub, n, indent + 1)
        return out
    return [pad + f"Bedingung «{k}»: " + fmt_data({a: b for a, b in c.items() if a != "condition"})]


def describe_actions(actions, n, indent=0):
    out = []
    pad = "  " * indent
    if isinstance(actions, dict):
        actions = [actions]
    for a in actions or []:
        if not isinstance(a, dict):
            out.append(pad + str(a))
            continue
        if a.get("enabled") is False:
            out.append(pad + "(deaktiviert) " + (a.get("alias") or "Schritt"))
            continue
        svc = a.get("action") or a.get("service")
        if svc:
            tgt = n.target(a.get("target") or ({"entity_id": a["entity_id"]} if a.get("entity_id") else {}))
            line = f"{svc}" + (f" auf {tgt}" if tgt else "")
            d = fmt_data(a.get("data"))
            out.append(pad + line + (f" ({d})" if d else ""))
        elif "delay" in a:
            out.append(pad + f"Warte {dur(a['delay'])}")
        elif "wait_for_trigger" in a:
            out.append(pad + "Warte auf: " + " / ".join(describe_trigger(t, n) for t in a["wait_for_trigger"]))
        elif "wait_template" in a:
            out.append(pad + f"Warte bis Template wahr: {a['wait_template']}")
        elif "choose" in a:
            out.append(pad + "Auswahl:")
            for i, opt in enumerate(a["choose"], 1):
                out.append(pad + f"  Fall {i} – wenn:")
                for c in opt.get("conditions", []):
                    out += describe_condition(c, n, indent + 2)
                out.append(pad + "  dann:")
                out += describe_actions(opt.get("sequence"), n, indent + 2)
            if a.get("default"):
                out.append(pad + "  Sonst:")
                out += describe_actions(a["default"], n, indent + 2)
        elif "if" in a:
            out.append(pad + "Wenn:")
            for c in a["if"]:
                out += describe_condition(c, n, indent + 1)
            out.append(pad + "dann:")
            out += describe_actions(a.get("then"), n, indent + 1)
            if a.get("else"):
                out.append(pad + "sonst:")
                out += describe_actions(a["else"], n, indent + 1)
        elif "repeat" in a:
            r = a["repeat"]
            kind = "für Anzahl " + str(r["count"]) if "count" in r else "while/until" if ("while" in r or "until" in r) else "für jedes Element" if "for_each" in r else ""
            out.append(pad + f"Wiederhole ({kind}):")
            out += describe_actions(r.get("sequence"), n, indent + 1)
        elif "parallel" in a:
            out.append(pad + "Parallel:")
            out += describe_actions(a["parallel"], n, indent + 1)
        elif "sequence" in a:
            out += describe_actions(a["sequence"], n, indent)
        elif "variables" in a:
            out.append(pad + "Variablen setzen: " + ", ".join(a["variables"].keys()))
        elif "event" in a:
            out.append(pad + f"Ereignis auslösen «{a['event']}»")
        elif "stop" in a:
            out.append(pad + f"Stopp: {a['stop']}")
        elif "condition" in a:
            out.append(pad + "Prüfe Bedingung (Abbruch wenn falsch):")
            out += describe_condition(a, n, indent + 1)
        elif "scene" in a:
            out.append(pad + f"Szene aktivieren: {a['scene']}")
        elif "device_id" in a:
            out.append(pad + f"Geräteaktion: {a.get('type')} (Gerät {a['device_id']})")
        else:
            out.append(pad + fmt_data(a))
    return out


# --------------------------------------------------------------------------
# 3. PDF
# --------------------------------------------------------------------------


def build_pdf(data, out_path, title="Home Assistant Dokumentation"):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                    Spacer, Table, TableStyle)
    from reportlab.platypus.tableofcontents import TableOfContents

    n = Namer(data)
    cfg = data["config"]
    ss = getSampleStyleSheet()
    ACC = colors.HexColor("#03a9f4")
    DARK = colors.HexColor("#1f2933")
    H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=DARK, fontSize=18, spaceBefore=6, spaceAfter=8)
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=ACC, fontSize=13, spaceBefore=10, spaceAfter=4)
    H3 = ParagraphStyle("H3", parent=ss["Heading3"], textColor=DARK, fontSize=10.5, spaceBefore=6, spaceAfter=2)
    BODY = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9, leading=12)
    SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, textColor=colors.grey)
    LINE = ParagraphStyle("L", parent=BODY, fontSize=8.5, leading=11, fontName="Courier")
    CELL = ParagraphStyle("C", parent=BODY, fontSize=8, leading=10)

    class Doc(BaseDocTemplate):
        def afterFlowable(self, fl):
            if isinstance(fl, Paragraph) and fl.style.name in ("H1", "H2"):
                self.notify("TOCEntry", (0 if fl.style.name == "H1" else 1, fl.getPlainText(), self.page))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(20 * mm, 10 * mm, f"{title} – {cfg.get('location_name', '')}")
        canvas.drawRightString(190 * mm, 10 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    doc = Doc(out_path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
              title=title, author="ha_doc")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)],
                                       onPage=footer)])

    def P(t, s=BODY):
        return Paragraph(escape(str(t)), s)

    def table(rows, widths, header=True):
        t = Table([[Paragraph(escape(str(c)), CELL) for c in r] for r in rows], colWidths=widths, repeatRows=1 if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fa")])]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e1f3fc"))]
        t.setStyle(TableStyle(style))
        return t

    W = doc.width
    story = []

    # Deckblatt
    story += [Spacer(1, 70 * mm), Paragraph(escape(title), ParagraphStyle("T", parent=H1, fontSize=30, leading=36)),
              Spacer(1, 6 * mm), P(cfg.get("location_name", "Home Assistant"), ParagraphStyle("T2", parent=BODY, fontSize=16, leading=20, textColor=ACC)),
              Spacer(1, 25 * mm),
              table([["Home Assistant Version", cfg.get("version", "?")], ["Zeitzone", cfg.get("time_zone", "?")],
                     ["Erstellt am", dt.datetime.now().strftime("%d.%m.%Y %H:%M")]], [50 * mm, 80 * mm], header=False),
              PageBreak()]

    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontSize=10, leftIndent=0, spaceBefore=4),
                       ParagraphStyle("t1", fontSize=9, leftIndent=12, textColor=colors.HexColor("#444444"))]
    story += [Paragraph("Inhaltsverzeichnis", ParagraphStyle("TH", parent=H1)), toc, PageBreak()]

    # Uebersicht
    doms = defaultdict(int)
    for s in data["states"]:
        doms[s["entity_id"].split(".")[0]] += 1
    unavailable = [s for s in data["states"] if s["state"] in ("unavailable", "unknown") and not s["entity_id"].startswith(("scene.", "button.", "automation.", "script."))]
    story.append(Paragraph("Übersicht", H1))
    story.append(table([["Kennzahl", "Anzahl"], ["Entitäten (aktiv)", len(data["states"])], ["Geräte", len(data["devices"])],
                        ["Bereiche", len(data["areas"])], ["Integrationen", len(data["entries"])],
                        ["Automatisierungen", len(data["automations"])], ["Skripte", len(data["scripts"])],
                        ["Szenen", len(data["scenes"])], ["Nicht verfügbare Entitäten", len(unavailable)]],
                       [90 * mm, 30 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Entitäten nach Domain", H2))
    top = sorted(doms.items(), key=lambda x: -x[1])
    story.append(table([["Domain", "Anzahl"]] + [[d, c] for d, c in top], [60 * mm, 30 * mm]))
    story.append(PageBreak())

    # Bereiche & Geraete
    dev_by_id = {d["id"]: d for d in data["devices"]}
    ents_by_dev = defaultdict(list)
    area_of_ent = {}
    for e in data["entities"]:
        if e.get("device_id"):
            ents_by_dev[e["device_id"]].append(e["entity_id"])
        area_of_ent[e["entity_id"]] = e.get("area_id") or (dev_by_id.get(e.get("device_id"), {}).get("area_id"))
    floors = {f["floor_id"]: f for f in data["floors"]}
    story.append(Paragraph("Bereiche und Geräte", H1))
    areas_sorted = sorted(data["areas"], key=lambda a: (floors.get(a.get("floor_id"), {}).get("level", 99), a["name"]))
    for a in areas_sorted + [{"area_id": None, "name": "Ohne Bereich", "floor_id": None}]:
        devs = [d for d in data["devices"] if d.get("area_id") == a["area_id"]]
        loose = [e for e, ar in area_of_ent.items() if ar == a["area_id"] and not next((x for x in data["entities"] if x["entity_id"] == e and x.get("device_id")), None)]
        if not devs and not loose:
            continue
        fl = floors.get(a.get("floor_id"), {}).get("name")
        block = [Paragraph(escape(a["name"] + (f"  ({fl})" if fl else "")), H2)]
        rows = [["Gerät", "Hersteller / Modell", "Entitäten"]]
        for d in devs:
            # Viele Entitäten auf mehrere Zeilen verteilen (sonst passt die Zelle nicht auf eine Seite)
            ents = ents_by_dev.get(d["id"], []) or [""]
            for i in range(0, len(ents), 10):
                first = i == 0
                rows.append([(d.get("name_by_user") or d.get("name") or "?") if first else "",
                             f"{d.get('manufacturer') or ''} {d.get('model') or ''}".strip() if first else "",
                             "\n".join(ents[i:i + 10])])
        for e in loose:
            rows.append(["(ohne Gerät)", "", e])
        block.append(table(rows, [50 * mm, 50 * mm, W - 100 * mm]))
        story.append(KeepTogether(block[:2]))
    story.append(PageBreak())

    # Integrationen
    story.append(Paragraph("Integrationen", H1))
    story.append(table([["Integration", "Domain", "Status", "Quelle"]] +
                       [[e.get("title"), e.get("domain"), e.get("state"), e.get("source")] for e in sorted(data["entries"], key=lambda x: x.get("domain", ""))],
                       [55 * mm, 40 * mm, 30 * mm, W - 125 * mm]))
    story.append(PageBreak())

    # Automatisierungen
    def render_items(heading, items, kind):
        story.append(Paragraph(heading, H1))
        if not items:
            story.append(P("Keine vorhanden."))
        for it in sorted(items, key=lambda x: (x["attrs"].get("friendly_name") or x["entity_id"]).lower()):
            c = it["config"]
            name = it["attrs"].get("friendly_name") or it["entity_id"]
            status = {"on": "aktiv", "off": "deaktiviert"}.get(it["state"], it["state"]) if kind == "automation" else ""
            blk = [Paragraph(escape(name), H3), P(it["entity_id"] + (f"  |  Status: {status}" if status else "") +
                   (f"  |  Modus: {c.get('mode') or it['attrs'].get('mode')}" if kind != "scene" and (c or it['attrs'].get('mode')) else ""), SMALL)]
            if c is None:
                blk.append(P("Konfiguration nicht über die API lesbar (z. B. in YAML definiert).", SMALL))
                story.append(KeepTogether(blk))
                continue
            if c.get("description"):
                blk.append(P(c["description"]))
            lines = []
            if kind == "automation":
                trig = c.get("triggers", c.get("trigger", []))
                cond = c.get("conditions", c.get("condition", []))
                act = c.get("actions", c.get("action", []))
                trig = [trig] if isinstance(trig, dict) else trig
                cond = [cond] if isinstance(cond, (dict, str)) else cond
                lines.append(("AUSLÖSER", [describe_trigger(t, n) for t in trig]))
                if cond:
                    cl = []
                    for x in cond:
                        cl += describe_condition(x, n)
                    lines.append(("BEDINGUNGEN (alle müssen zutreffen)", cl))
                lines.append(("AKTIONEN", describe_actions(act, n)))
                la = it["attrs"].get("last_triggered")
                if la:
                    blk.append(P(f"Zuletzt ausgelöst: {la[:16].replace('T', ' ')}", SMALL))
            elif kind == "script":
                lines.append(("ABLAUF", describe_actions(c.get("sequence"), n)))
            else:
                lines.append(("ENTITÄTEN", [f"{n.ent(e)} -> {v.get('state', '') if isinstance(v, dict) else v}" for e, v in (c.get("entities") or {}).items()]))
            for lab, ls in lines:
                blk.append(P(lab, ParagraphStyle("lab", parent=SMALL, textColor=ACC, spaceBefore=3)))
                for l in ls or ["(leer)"]:
                    stripped = l.lstrip(" ")
                    ind = len(l) - len(stripped)
                    blk.append(Paragraph(escape(stripped), ParagraphStyle("li", parent=LINE, leftIndent=4 + ind * 3.5)))
            story.append(KeepTogether(blk[:4]))
            story.extend(blk[4:])
        story.append(PageBreak())

    render_items("Automatisierungen", data["automations"], "automation")
    render_items("Skripte", data["scripts"], "script")
    render_items("Szenen", data["scenes"], "scene")

    # Helfer
    helper_doms = ("input_boolean", "input_number", "input_select", "input_text", "input_datetime", "input_button", "counter", "timer", "schedule")
    helpers = [s for s in data["states"] if s["entity_id"].split(".")[0] in helper_doms]
    story.append(Paragraph("Helfer", H1))
    story.append(table([["Name", "Entität", "Typ", "Aktueller Wert"]] +
                       [[s["attributes"].get("friendly_name", ""), s["entity_id"], s["entity_id"].split(".")[0], s["state"]] for s in sorted(helpers, key=lambda x: x["entity_id"])],
                       [45 * mm, 60 * mm, 30 * mm, W - 135 * mm]) if helpers else P("Keine vorhanden."))
    story.append(PageBreak())

    # Probleme
    story.append(Paragraph("Auffälligkeiten", H1))
    story.append(Paragraph("Nicht verfügbare Entitäten", H2))
    story.append(table([["Entität", "Name", "Status"]] + [[s["entity_id"], s["attributes"].get("friendly_name", ""), s["state"]] for s in unavailable],
                       [70 * mm, 60 * mm, W - 130 * mm]) if unavailable else P("Keine."))
    # Referenzen: Entitaeten in Automationen, die nicht (mehr) existieren
    known = {s["entity_id"] for s in data["states"]}
    broken = []
    for coll in (data["automations"], data["scripts"], data["scenes"]):
        for it in coll:
            if not it["config"]:
                continue
            for ref in sorted(set(_find_entity_refs(it["config"]))):
                if ref not in known and ref != "all":
                    broken.append([it["attrs"].get("friendly_name") or it["entity_id"], ref])
    story.append(Paragraph("Referenzen auf nicht existierende Entitäten", H2))
    story.append(table([["Verwendet in", "Fehlende Entität"]] + broken, [80 * mm, W - 80 * mm]) if broken else P("Keine."))

    doc.multiBuild(story)


def _find_entity_refs(obj):
    import re
    pat = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
    skip = ("light", "switch", "sensor", "binary_sensor", "cover", "climate", "person", "input_boolean", "input_number", "input_select",
            "input_text", "input_datetime", "scene", "script", "automation", "media_player", "fan", "lock", "timer", "counter",
            "device_tracker", "zone", "sun", "weather", "camera", "vacuum", "button", "number", "select", "calendar", "group")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "entity_id":
                for x in (v if isinstance(v, list) else [v]):
                    if isinstance(x, str) and pat.match(x) and x.split(".")[0] in skip:
                        yield x
            else:
                yield from _find_entity_refs(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _find_entity_refs(x)


# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Home Assistant Dokumentation als PDF")
    ap.add_argument("--url", help="z. B. http://homeassistant.local:8123")
    ap.add_argument("--token", help="Langlebiges Zugriffstoken")
    ap.add_argument("--demo", action="store_true", help="Beispieldaten verwenden")
    ap.add_argument("--dump-json", help="Rohdaten zusätzlich als JSON speichern")
    ap.add_argument("-o", "--output", default="ha_dokumentation.pdf")
    a = ap.parse_args()
    if a.demo:
        data = demo_data()
    elif a.url and a.token:
        data = fetch_all(a.url, a.token)
    else:
        ap.error("Entweder --demo oder --url und --token angeben.")
    if a.dump_json:
        with open(a.dump_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    build_pdf(data, a.output)
    print(f"Fertig: {a.output}")


if __name__ == "__main__":
    sys.exit(main())
