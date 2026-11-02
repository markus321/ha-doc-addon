# Änderungen

## 0.3.1
- Excel-Export: Geräteliste mit eingeklappten Entitäten (aufklappbar über die Gruppierung am linken Rand), dazu Blätter «Netzwerk» und «Integrationen».

## 0.3.0
- Neuer Abschnitt «Netzwerk»: IP, MAC, Hersteller, VLAN und WLAN/LAN der Geräte, gruppiert nach VLAN. Nur mit UniFi-Gateway oder Fritz!Box.
- Bei Geräten mit passender MAC-Adresse wird die IP in der Gerätetabelle angezeigt.

## 0.2.3
- Monatsbericht nutzt die in der Oberfläche gespeicherte Auswahl («Auswahl für Monatsbericht speichern»), inklusive Bereichen. Die Konfiguration dient als Ersatz.

## 0.2.2
- Konfiguration: Abschnitte des Monatsberichts sind jetzt einzelne Schalter statt einer Liste (die Liste liess sich nicht bearbeiten).

## 0.2.1
- Oberfläche folgt dem Dunkelmodus von Home Assistant.
- Monatsbericht: gleiche Filter wie in der Oberfläche (Diagnose-Entitäten, nur fehlende Entitäten, bestimmte Bereiche).

## 0.2.0
- Auswahl vor dem Erstellen: einzelne Bereiche, Diagnose-Entitäten ausblenden, nur Einträge mit fehlenden Entitäten.
- Monatlicher Bericht mit Aufbewahrung der letzten PDFs.
- Symbol, Logo, README und Übersetzungen.

## 0.1.6
- Blueprint-Automatisierungen: Name, Beschreibung und nur die vom Standard abweichenden Eingaben.
- Fehlende Entitäten in Blueprint-Eingaben werden gefunden.

## 0.1.5
- Automatisierungen als Schema (Auslöser → Bedingungen → Aktionen), auswählbar.

## 0.1.4
- Ein Kasten pro Gerät mit allen Entitäten und wiederholter Kopfzeile auf Folgeseiten.

## 0.1.3
- Gleichartige Auslöser werden zusammengefasst, uninteressante Dienste aus der Liste nicht verfügbarer Entitäten entfernt.
- Auswahl der Abschnitte vor dem Erstellen.

## 0.1.2
- Fehler behoben: Geräte mit sehr vielen Entitäten führten zu einem Abbruch beim Erstellen des PDFs.

## 0.1.1
- Aufbau des Images repariert (Python-Basisimage).

## 0.1.0
- Erste Version.
