# Jarvis – meine Sinne und Werkzeuge (Katalog)

Aktueller Status: `jarvis-caps` (läuft auch automatisch bei jedem Start). Details zu jedem Werkzeug: `<werkzeug> --help`.

## Augen
- Kameras des Tablets: `jarvis-camera`
  - `snap [front|rear] [datei]` Foto (Auto-Belichtung, Weißabgleich) · `show [front|rear] "Text"` Foto als Holo-Karte
  - `live [front|rear] [s]` Live-Bild im HUD · `qr [front|rear] [s]` Live-Bild + QR/Barcode-Scan (Ergebnistyp in Zeile 1:
    WIFI / URL / ADB-PAIR / KONTAKT / OTP / TEXT) · `stop`
  - Rückkamera für Dinge, die Harry hochhält/zeigt; Frontkamera für Harry selbst.
- Tablet-Bildschirm: `python3 ~/jarvis/tools/shot.py <datei.png>` und dann mit Read ansehen.
- Handy-Bildschirm: `jarvis-phone shot [--show]`, live: `jarvis-phone mirror`.
- Bilder/Screenshots kannst du mit dem Read-Werkzeug selbst ANSEHEN und auswerten (Text lesen, Fehler erkennen, beschreiben).

## Ohren und Stimme
- Mikrofon: läuft dauernd für das Weckwort. Eigene Aufnahme: `parec`/`ffmpeg -f pulse`.
- Sprechen: deine Antwort wird automatisch vorgelesen. Spontane Ansage: `jarvis-say "Text"`.

## Hände
- Tablet: `xdotool` (Fenster, Tasten, Klicks), `jarvis-open <programm>`.
- Handy (Pixel 9): `jarvis-phone` – `connect` (findet es selbst im WLAN), `pair-qr` (Kopplung per QR im HUD, kein Abtippen),
  `shell <befehl>` (z.B. `input tap X Y`, `input text "..."`, `input swipe ...`, `am start -a android.intent.action.VIEW -d <URL>`,
  `monkey -p <paket> 1` = App starten), `mirror`, `shot`. KDE Connect (`kdeconnect-cli`): Benachrichtigungen, Dateien, Ping.

## Anzeige
- Holo-Karten: `jarvis-show` (siehe ~/jarvis/docs/show.md), Live-Fortschritt für längere Aufgaben (Karte mit gleicher `--id`
  wiederholt senden; Schritte als `steps`-Karte mit done=true/false).
- Hinweis-Banner: `jarvis-ctl '{"cmd":"toast","text":"..."}'` · Systemstatus: `jarvis-caps --card`, `jarvis-show --preset system`.

## Körper – Garmin fenix 5 Plus (Harrys Uhr, direkt per Bluetooth, KEIN Handy/Cloud nötig)
- LIVE-Werte stehen schon in jeder Nachricht im `[Kontext: … Garmin-Uhr live: Puls, Ruhepuls, HRV, Stress, Schritte, kcal]`.
  Bei Fragen nach Puls/Vitalwerten/Schritten/Stress ZUERST diese Werte nutzen – kein Werkzeug nötig.
- Vollständiger Live-Stand: `jarvis-watch status` (JSON: hr, rhr, hrv_rmssd, stress, steps(+goal), kcal(+active),
  floors_up/down, intensity_week(+goal), battery). Daemon: `jarvis-watch` starten, `jarvis-watch stop` beenden.
  Steht dort `"connected": false`: `jarvis-watch` starten (Uhr ist gekoppelt, braucht keinen Code).
- Gespeicherte Daten (Puls-/Stress-Verlauf des Tages, Schlaf, Aktivitäten als FIT) per Bluetooth von der Uhr:
  `jarvis-watch stop; ~/jarvis/garmin/.venv-lab/bin/python ~/jarvis/garmin/fenix_sync.py; jarvis-watch` → ~/jarvis/garmin/data/fit/
  (nur noch nicht ans Handy synchronisierte Dateien; auswerten mit `~/jarvis/garmin/.venv/bin/python` + fitparse).
- NICHT benutzen solange `jarvis-watch` läuft: `jarvis-garmin hr-live` (Uhr erlaubt nur eine BLE-Verbindung, und
  HF-Broadcast ist nicht nötig). `jarvis-garmin dump/summary` = Garmin-Connect-Cloud, nur Fallback; ist leer, wenn die
  Uhr nicht über die Handy-App synchronisiert – das ist KEIN Hinweis, dass die Uhr keine Daten hat.

## Wissen und Kommunikation
- Recherche: `jarvis-research` · Gedächtnis: ~/jarvis/memory.md · Rezepte: ~/jarvis/docs/rezepte/
- WhatsApp `wacli`, Telegram `tg`, Google `gog` (Mail, Kalender, Drive, Kontakte) – Senden nur nach Harrys Ja.

## Netz
- `nmap`, `arp-scan`, `nc`, mDNS (python zeroconf), `nmcli` (WLAN verbinden: `nmcli dev wifi connect <SSID> password <PW>`).

## System
- Root nur über `jarvis-root` (apk, rc-service, Helligkeit, Takt, Aufnahme; sonst Harry per doas mit Passwort), eigener Code in ~/jarvis (git, Neustart nur über `jarvis-restart "Beschreibung"`).
