# HA Doku – Home Assistant Add-on

Erstellt per Knopfdruck (oder automatisch jeden Monat) ein **PDF** deiner Home-Assistant-Installation:
Bereiche, Geräte und Entitäten, Integrationen, Automatisierungen, Skripte, Szenen, Helfer und Auffälligkeiten.
Alles läuft lokal in deinem Home Assistant, es werden keine Daten nach aussen gesendet.

*Creates a PDF documentation of your Home Assistant setup (areas, devices, automations, scripts, scenes, helpers and issues) – locally, on demand or monthly.*

## Funktionen

- **Auswahl vor dem Erstellen:** Abschnitte, einzelne Bereiche, Diagnose-Entitäten ausblenden, nur Einträge mit fehlenden Entitäten.
- **Ein Kasten pro Gerät** mit Gerätename, Hersteller/Modell und allen Entitäten (mit Namen).
- **Automatisierungen als Text und als Schema** (Auslöser → Bedingungen → Aktionen), gleichartige Auslöser zusammengefasst.
- **Blueprints:** Name, Beschreibung und nur die vom Standard abweichenden Eingaben.
- **Auffälligkeiten:** nicht verfügbare Entitäten und Verweise auf Entitäten, die es nicht mehr gibt (auch in Blueprint-Eingaben).
- **Monatlicher Bericht** optional, mit Aufbewahrung der letzten N PDFs.

| Geräte | Automatisierung als Schema | Blueprint |
|---|---|---|
| ![Geräte](docs/geraete.png) | ![Schema](docs/automation.png) | ![Blueprint](docs/blueprint.png) |

*(Beispielbilder mit Demodaten.)*

## Installation

1. In Home Assistant: **Einstellungen › Add-ons › Add-on-Store › ⋮ › Repositories** und diese Adresse hinzufügen:
   `https://github.com/markus321/ha-doc-addon`
2. **HA Doku (PDF)** installieren und starten, «In Seitenleiste anzeigen» aktivieren.
3. In der Seitenleiste **HA Doku** öffnen, Abschnitte wählen und **PDF erstellen**.

Die PDFs liegen in der Freigabe `share` im Ordner `ha_doc`.

Voraussetzung: Home Assistant OS oder Supervised (Add-ons), Architektur amd64 oder aarch64.

## Monatlicher Bericht

Unter **Konfiguration** des Add-ons «Monatlichen Bericht erstellen» einschalten, Tag und Uhrzeit wählen. Abschnitte und Filter (Diagnose-Entitäten, nur fehlende Entitäten, bestimmte Bereiche) lassen sich dort wie in der Oberfläche festlegen.
Damit der Bericht wirklich erstellt wird, muss das Add-on laufen: **«Beim Systemstart starten»** einschalten.

## Datenschutz

Das Add-on liest die Konfiguration deines Home Assistant über die interne Schnittstelle (Supervisor) und schreibt PDFs in `share/ha_doc`.
Es sendet nichts ins Internet. Das PDF enthält Namen und IDs deiner Geräte und Entitäten – gib es mit Bedacht weiter.

## Bekannte Grenzen

- Automatisierungen, die in YAML ohne ID definiert sind, sind über die Schnittstelle nicht lesbar und erscheinen mit Hinweis.
- Vom Blueprint selbst werden Auslöser und Aktionen nicht dargestellt, nur seine Eingaben.
- Add-ons und Netzwerk-Topologie (z. B. Zigbee) sind noch nicht enthalten.
