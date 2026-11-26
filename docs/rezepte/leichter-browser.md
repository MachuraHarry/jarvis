# Leichtgewichtiger Browser auf dem Tablet (NetSurf)
Wann: Harry will einen Browser, der wenig RAM und CPU braucht, oder Firefox ist zu schwer.
## Schritte
1. Installation: `jarvis-root apk add netsurf` (Paket ca. 6 MB, liefert netsurf-gtk3 und netsurf).
2. Starten: `jarvis-open netsurf-gtk3 <url>`.
3. Speicher prüfen: `ps -o rss=,comm= -C netsurf-gtk3` (RSS etwa 45 MB) gegen Firefox.
## Stolperfallen
- NetSurf kann nur eingeschränkt JavaScript; Seiten mit viel JS funktionieren schlechter als in Firefox.
- Für reine Textseiten ginge auch dillo (apk add dillo), noch kleiner, aber ohne JS.
Zuletzt geprüft: 26.11.2026
