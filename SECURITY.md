# Sicherheit

## Bedrohungsmodell

Jarvis' Gehirn ist `claude -p --permission-mode bypassPermissions`. Es hat volle Shell-Rechte als Benutzer.
Root bekommt es nur über die geprüfte Schnittstelle `jarvis-root` (siehe unten). Gleichzeitig liest es **nicht vertrauenswürdige Inhalte**: Webseiten,
Mails, WhatsApp- und Telegram-Nachrichten. Das Hauptrisiko ist deshalb **Prompt Injection**: Ein präparierter
Text bringt das Modell dazu, Daten abfließen zu lassen, Nachrichten in fremdem Namen zu senden, sich
einzunisten oder etwas zu zerstören.

Nicht im Modell: physischer Zugriff auf das Gerät, kompromittierte Systempakete.

## Schutzschichten

1. **Wächter (`hooks/guard.py`)** als Claude-Code-Hook vor jedem Bash-, Write-, Edit-, Read- und WebFetch-Aufruf:
   - **Immer blockiert:** unwiderruflich destruktive Befehle (`rm -rf` auf Home, System oder `*`, `mkfs`, `dd of=/dev/…`, `shred`, Forkbomb). Ebenso jede Änderung an Wächter, Git-Hooks und `system/`. `git push` braucht immer eine Freigabe.
   - **Nach fremden Inhalten („Taint“, 45 min):** Senden von Nachrichten, `curl|sh`, Datenabfluss (`curl -d/-F/-T`, `nc`, `scp`, `rsync`/`ssh` nach außen, `/dev/tcp`, lange Query-URLs per WebFetch), Zugriff auf Zugangsdaten (`~/.ssh`, Token-Verzeichnisse, Claude-Credentials) und Persistenz (Shell-Profile, Autostart, cron, `/etc`, `bin/`).
   - **Freigabe:** Nur ein „Ja“, das Harry selbst spricht oder tippt, gibt frei, und zwar genau die zuletzt blockierte Aktion, einmalig. Nachrichten über den Skript-Socket zählen nicht als Zustimmung.
   - **Fail-closed:** Stürzt der Wächter ab, wird die Aktion blockiert (Exit 2).
   - **Speicherschutz:** `apk add` wird blockiert, wenn die kleine Systempartition volllaufen würde.
2. **HUD:** Fremdinhalte werden ausschließlich per `textContent` gerendert (kein `innerHTML`). WebKit läuft ohne WebGL, Media, Storage und Dev-Tools. Die Bridge übergibt Nachrichten JSON-kodiert.
3. **Root-Begrenzung (`system/`):** doas erlaubt passwortlos nur `/usr/local/libexec/jarvis/jarvis-root`. Die Datei ist root-eigen und für den Benutzer nicht beschreibbar. Jeder Unterbefehl prüft seine Argumente streng:
   - `apk add|del` nur mit Paketnamen aus dem Repo, ohne Optionen und ohne lokale Dateien
   - `rc-service` nur für vorhandene Dienste und feste Aktionen
   - Helligkeit, CPU-Mindesttakt, Prozess-Priorität (nur für eigene Prozesse), KMS-Bildschirmaufnahme mit festen ffmpeg-Argumenten
   - nmap läuft mit Capabilities statt Root.

   Für alles andere fragt doas nach dem Passwort des Menschen. `jarvis-doctor` warnt, falls wieder pauschales nopass aktiv ist, z. B. nach einem Paket-Update.
4. **Git:** Ein Pre-commit-Hook blockiert private Pfade, große Dateien und Secret-Muster in Auto-Commits. `git push`, `git remote add/set-url`, `--no-verify` und `core.hooksPath` brauchen immer eine Freigabe.
5. **Socket:** Unix-Socket unter `/run/user/<uid>/` mit Rechten `0600`.
6. **Pentest-Werkzeuge:** `jarvis-pentest` erzwingt eine Scope-Liste (eigenes Netz, localhost). Fremde Ziele brauchen eine ausdrückliche Freigabe.
7. **Repo-Hygiene:** Persönliche Daten, Gesundheitsdaten, Scan-Ergebnisse und die Config sind nicht im Repo. CI führt gitleaks aus.

## Bekannte Grenzen (ehrlich)

- Der Wächter arbeitet mit **Mustern, nicht mit einer Sandbox**. Ein entschlossenes Modell kann ihn mit Kodierung, Umwegen über Skriptdateien oder anderen Interpretern umgehen. Er senkt das Risiko, beseitigt es aber nicht.
- `jarvis-root apk add` installiert beliebige Repo-Pakete. Deren Install-Skripte laufen als root. Vertraut wird hier den signierten Alpine/pmOS-Repos.
- Der Benutzer-Account selbst (Dateien, Mails, Tokens) ist für das Gehirn voll zugänglich. Die Root-Begrenzung schützt das System, nicht die Benutzerdaten.
- WebSearch-Anfragen selbst werden nicht geprüft.

## Meldung von Schwachstellen

Bitte als privates GitHub Security Advisory in diesem Repo melden, nicht als öffentliches Issue.
