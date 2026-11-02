# HA Doku (PDF)

Seitenleiste → **HA Doku** → Abschnitte und Optionen wählen → **PDF erstellen**.
Die PDFs liegen in der Freigabe `share`, Ordner `ha_doc`.

## Optionen im PDF

- **Abschnitte:** Übersicht, Bereiche und Geräte, Integrationen, Automatisierungen (Text und/oder Schema), Skripte, Szenen, Helfer, Auffälligkeiten.
- **Bereiche auswählen:** nur einzelne Bereiche dokumentieren.
- **Konfigurations-/Diagnose-Entitäten ausblenden:** kürzere Geräteliste.
- **Nur Einträge mit fehlenden Entitäten:** zeigt Automatisierungen, Skripte und Szenen, die auf nicht mehr vorhandene Entitäten verweisen.

## Konfiguration (Monatsbericht)

| Option | Bedeutung |
|---|---|
| schedule_enabled | Monatlichen Bericht automatisch erstellen |
| schedule_day | Tag im Monat (1–28) |
| schedule_time | Uhrzeit `HH:MM` (Zeitzone von Home Assistant) |
| keep_last | Anzahl aufbewahrter PDFs (ältere werden gelöscht) |

Der automatische Bericht enthält alle Abschnitte und blendet Konfigurations-/Diagnose-Entitäten aus.
Das Add-on muss laufen, schalte dafür **Beim Systemstart starten** ein.
