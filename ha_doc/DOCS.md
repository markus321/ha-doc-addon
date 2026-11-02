# HA Doku (PDF)

Seitenleiste → **HA Doku** → Abschnitte und Optionen wählen → **PDF erstellen**.
Die PDFs liegen in der Freigabe `share`, Ordner `ha_doc`.

## Optionen im PDF

- **Abschnitte:** Übersicht, Bereiche und Geräte, Integrationen, Automatisierungen (Text und/oder Schema), Skripte, Szenen, Helfer, Auffälligkeiten.
- **Bereiche auswählen:** nur einzelne Bereiche dokumentieren.
- **Konfigurations-/Diagnose-Entitäten ausblenden:** kürzere Geräteliste.
- **Nur Einträge mit fehlenden Entitäten:** zeigt Automatisierungen, Skripte und Szenen, die auf nicht mehr vorhandene Entitäten verweisen.

## Konfiguration (Monatsbericht)

Der Monatsbericht kann dieselben Filter nutzen wie die Oberfläche:

| Option | Bedeutung |
|---|---|
| schedule_enabled | Monatlichen Bericht automatisch erstellen |
| schedule_day | Tag im Monat (1–28) |
| schedule_time | Uhrzeit `HH:MM` (Zeitzone von Home Assistant) |
| keep_last | Anzahl aufbewahrter PDFs (ältere werden gelöscht) |
| schedule_uebersicht … schedule_auffaelligkeiten | Ein Schalter pro Abschnitt im Bericht (Standard: alle an) |
| schedule_hide_diagnostic | Konfigurations-/Diagnose-Entitäten ausblenden (Standard: ja) |
| schedule_only_problems | Nur Einträge mit fehlenden Entitäten |
| schedule_areas | Nur diese Bereiche (Namen); leer = alle |

Die Abschnitte: `uebersicht`, `bereiche`, `integrationen`, `automatisierungen` (Text), `schema` (Automatisierungen als Schema), `skripte`, `szenen`, `helfer`, `auffaelligkeiten`.

Das Add-on muss laufen, schalte dafür **Beim Systemstart starten** ein.
