# Garmin-Uhr auswerten (Puls, Stress, Sync)
Wann: Harry fragt nach Puls- oder Stressverlauf des Tages, nach Auswertung, Schlaf oder "synchronisiere die Uhr".

Schritte:
1. Lokale Daten auswerten: `~/jarvis/bin/jarvis-garmin-auswertung`
2. Wenn Harry frische Daten will: `~/jarvis/bin/jarvis-garmin-auswertung --sync` (Live-Daemon kurz aus, danach wieder an).
3. Cloud-Zusammenfassung zusätzlich: `--cloud` (leer, wenn nicht über die Handy-App synchronisiert).

Bekannte Grenzen:
- Schlaf aus den FIT-Dateien ist nicht decodiert (unbekannte Nachrichtentypen).
- Negative Stresswerte sind Messfehler und werden ausgeschlossen.
- Die Uhr hat nur eine Bluetooth-Verbindung: während des Syncs ist der Live-Daemon aus.

Stand: 25.11.2026, Auswertung getestet.
