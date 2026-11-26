# J.A.R.V.I.S. – autonomer Sprachassistent für ein Linux-Tablet

[![CI](https://github.com/MachuraHarry/jarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/MachuraHarry/jarvis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Ein deutschsprachiger Sprachassistent, der als Desktop-HUD auf einem Samsung Galaxy Tab A 10.1 (SM-T510) mit
**postmarketOS (Alpine Linux, XFCE/X11)** läuft. Wie das Gerät überhaupt bootet, steht in
[pmos-samsung-gta3xlwifi](https://github.com/MachuraHarry/pmos-samsung-gta3xlwifi). Gehirn ist ein dauerhaft laufender
[Claude Code](https://claude.com/claude-code)-Prozess (`claude -p`, stream-json) mit Shell-Zugriff. Ohren,
Stimme, Anzeige und Werkzeuge sind lokal.

```
 Mikrofon ─► Vosk (offline, Weckwort) ─► Google STT (optional) ─┐
                                                               ▼
  HUD (WebKitGTK) ◄── UI-Bridge ◄── jarvis.py ──► claude -p (stream-json) ──► Werkzeuge (bin/jarvis-*)
       ▲                               │                 │
       └─ Karten (jarvis-show)         │                 └─ Hooks: hooks/guard.py (Sicherheits-Wächter)
                                       ▼
                         TTS: Edge-Neural (online) / Piper (offline)
```

## Fähigkeiten

- **Sprache:** Weckwort „Jarvis“ offline per Vosk. Befehle werden optional online genauer erkannt. Antworten werden gestreamt und satzweise vorgelesen.
- **HUD:** Vollbild-Oberfläche als Desktop mit Status, Wetter, Protokoll, WLAN-Manager und Holo-Karten (Mail, Chats, Bilder, Fortschritt).
- **Körper:** Kameras (Foto, Live, QR), Steuerung des Handys per adb, Bildschirmaufnahme, Lautstärke und Helligkeit, Power-Taste, Garmin-Uhr per BLE.
- **Wissen:** Recherche-Agent (`jarvis-research`), Chronik als Gesprächsgedächtnis, selbst geschriebene „Rezepte“ (`docs/rezepte/`).
- **Selbstwartung:** `jarvis-restart` prüft Syntax und Selbsttest, committet und startet neu. Bei Fehlstart rollt es automatisch auf den Git-Tag `good` zurück. `jarvis-doctor` liefert die Diagnose.

Alle Werkzeuge stehen in [`docs/faehigkeiten.md`](docs/faehigkeiten.md).

## Aufbau

| Pfad | Inhalt |
|---|---|
| `app/jarvis.py` | Hauptprozess: Ohren, Stimme, Gehirn, HUD-Bridge, Socket |
| `app/ui/` | HUD (HTML/CSS/JS, nur `textContent` für Fremdinhalte) |
| `hooks/guard.py` | Sicherheits-Wächter (Claude-Code-Hooks), siehe [SECURITY.md](SECURITY.md) |
| `system/` | Root-Schnittstelle `jarvis-root` und doas-Regel (einziger passwortloser Root-Weg) |
| `tools/git-hooks/` | Pre-commit-Wächter gegen Secrets/Privates in Auto-Commits |
| `bin/` | Werkzeuge, die das Gehirn aufruft |
| `persona.md` | System-Prompt (Persönlichkeit, Regeln, Werkzeugliste) |
| `garmin/` | BLE-Anbindung einer Garmin fenix 5 Plus |
| `tests/selftest.py` | Selbsttest ohne GTK/Audio/Netz (läuft auch in CI) |

## Installation (Kurzfassung)

```sh
git clone <repo> ~/jarvis && cd ~/jarvis
doas apk add py3-gobject3 webkit2gtk-4.1 pulseaudio-utils ffmpeg mpg123 espeak-ng xdotool
pip install --user -r requirements.txt
tools/fetch-models.sh                 # Vosk- und Piper-Modelle
cp config.example.json config.json    # Name, Standort, optional google_stt_key
git config core.hooksPath tools/git-hooks
doas sh system/install.sh             # Root-Helfer + nmap-Capabilities
doas sh system/install.sh --activate  # optional: Root sonst nur noch mit Passwort (empfohlen)
python3 tests/selftest.py
./run.sh                              # bzw. per ~/.xprofile beim Login starten
```

Voraussetzung ist ein angemeldetes `claude` (Claude Code CLI) im `PATH`. Persönliche Daten wie `config.json`,
`memory.md`, `state/`, Garmin-Daten und Pentest-Ergebnisse sind per `.gitignore` ausgeschlossen.

## Selbstverwaltender Code

Jarvis ändert seinen eigenen Code. `jarvis-restart` committet diese Änderungen als Autor **Jarvis**, bevor neu
gestartet wird. Das sind die Commits mit „Jarvis“ in der Historie. Ein Pre-commit-Hook verhindert, dass dabei private
Dateien oder Secrets ins Repo gelangen. `git push` braucht immer eine menschliche Freigabe.

## Sicherheit

Jarvis ist ein **autonomer Agent mit Shell-Zugriff und eng begrenzten Root-Rechten, der fremde Inhalte liest** (Web, Mail, Messenger). Das ist
bewusst so gebaut und nur auf einem dedizierten Gerät vertretbar. Bedrohungsmodell, Schutzmaßnahmen und
bekannte Grenzen stehen in [SECURITY.md](SECURITY.md).

## Credits

- [Claude Code](https://claude.com/claude-code) von Anthropic – das Gehirn
- [Vosk](https://alphacephei.com/vosk/) (Apache-2.0) – Offline-Spracherkennung, Modell `vosk-model-small-de-0.15`
- [Piper](https://github.com/rhasspy/piper) (Stimme `de_DE-karlsson-low`) und [edge-tts](https://github.com/rany2/edge-tts) – Sprachausgabe
- [garmin-proto-lab](garmin/) – BLE-Protokoll der Garmin-Uhr (nicht im Repo enthalten, wird separat installiert)
- Schriften Orbitron, Rajdhani, Share Tech Mono – SIL Open Font License, siehe `app/ui/fonts/OFL-*.txt`
- [postmarketOS](https://postmarketos.org) und die Arbeit von Mollomm1 am Geräteport

## Lizenz

[MIT](LICENSE) © 2026 Harry Machura. Die Schriften stehen unter der SIL OFL 1.1.
