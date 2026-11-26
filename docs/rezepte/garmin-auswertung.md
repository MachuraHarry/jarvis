# Garmin-Uhr auswerten (Puls, Stress, Schlaf, Route, Sync)
Wann: Harry fragt nach Puls- oder Stressverlauf des Tages, nach Auswertung, Schlaf, einer GPS-Strecke
(Lauf/Fahrt/Wanderung), oder "synchronisiere die Uhr".

Schritte:
1. Lokale Daten auswerten: `~/jarvis/bin/jarvis-garmin-auswertung` (Puls, Stress, Schlafphasen-Minuten)
2. GPS-Route der letzten Aktivität: `~/jarvis/bin/jarvis-garmin-auswertung --route`
3. Wenn Harry frische Daten will: `--sync` davor/zusätzlich (Live-Daemon kurz aus, danach wieder an).
4. Cloud-Zusammenfassung zusätzlich: `--cloud` (leer, wenn nicht über die Handy-App synchronisiert).

Technik (2026-11-26 überarbeitet): nutzt jetzt `garmin_proto_lab.fit` (`.venv-lab`) statt der
generischen `fitparse`-Bibliothek (`.venv`) – `fitparse` kennt Garmins eigene Wellness-Nachrichten
(Schlafphasen, Aktivitäts-GPS-Records) nicht und zeigt sie nur als `unknown_<nr>`.

Mit echten Daten geprüfte Ergebnisse/Grenzen (nicht nur angenommen):
- Puls/Stress: funktionieren korrekt, echte Felder sind `heart_rate_bpm` (Kind `monitoring`) und
  `stress_level` (Kind `stress`, negative Werte = Messfehler, werden ausgeschlossen).
- Schlafphasen (`sleep_level`): wird korrekt decodiert (echte Zeitstempel + Stufen wie `awake`,
  vermutlich auch `light`/`deep`/`rem` bei echtem Nachtschlaf) – bisher lagen nur Tages-/Ruhephasen
  lokal vor, daher noch keine Stufenvielfalt gesehen. Die rohen `sleep_data_raw`-Samples bleiben
  unentschlüsselt (verschlüsselte/proprietäre Rohbytes), werden nicht für die Auswertung gebraucht.
- GPS-Route (`--route`, aus `activity`-FIT-Dateien via `extract_activity_samples`): Code steht und
  liefert bei Vorhandensein Start/Ende-Koordinaten, Distanz, Puls-Mittel und einen OSM-Link zum
  Startpunkt. **Noch nicht mit echter Aktivität endverifiziert** – auf der Uhr lag beim Bau keine
  einzige `activity`-Datei (Harry hat aktuell keine GPS-Aktivität aufgezeichnet). Vor dem ersten
  Vertrauen auf eine echte Route: Harry bitten, eine kurze GPS-Aktivität zu starten+beenden,
  `--sync --route` laufen lassen und das Ergebnis gegen die bekannte Strecke prüfen.
- SpO2, Body Battery, Beschleunigungssensor: Live-Registrierung am echten Gerät getestet (nicht nur
  vermutet) – die fenix 5 Plus lehnt alle drei Dienste ab, weder live noch in FIT-Dateien vorhanden.
  Vermutlich Firmware-/Hardware-Grenze dieses (2018er) Modells, kein Jarvis-Bug. Nicht erneut versuchen,
  ohne neue Erkenntnisse (z.B. Firmware-Update der Uhr).
- Die Uhr hat nur eine Bluetooth-Verbindung: während des Syncs ist der Live-Daemon aus.

Stand: 26.11.2026, Puls/Stress/Schlaf-Auswertung mit echten Daten geprüft; Route-Code steht, braucht
noch eine echte Aktivität zum Endtest.
