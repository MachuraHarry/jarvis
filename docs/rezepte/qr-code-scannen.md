# QR-Code / Barcode mit der Tablet-Kamera scannen und verwerten
Wann: Harry will dir einen QR-Code zeigen (WLAN-Zugang, Link, Kontakt, Kopplungscode, Ticket …) oder sagt "scann mal".
## Schritte
1. Kurz sagen: "Halt den Code vor die Rückkamera." Dann `jarvis-camera qr rear 90` (Live-Bild erscheint im HUD).
   Hält er ihn vor das Display/sich selbst: `jarvis-camera qr front 90`.
2. Ergebnis verwerten – SELBSTSTÄNDIG, ohne nachzufragen:
   - WIFI → `nmcli dev wifi connect "<SSID>" password "<PASSWORT>"` und Erfolg melden
   - URL → zeigen (jarvis-open firefox <URL> bzw. auf dem Handy öffnen, wenn Harry das will) und kurz sagen, wohin sie führt
   - KONTAKT (vCard) → als Karte anzeigen; speichern nur auf Wunsch
   - OTP (2FA-Schlüssel) → NICHT vorlesen, nur bestätigen, dass es ein 2FA-Code ist, und fragen, wohin damit
   - TEXT → anzeigen und vorlesen
3. Bei "NICHTS": Licht/Abstand ansprechen (10–20 cm, Code ruhig halten) und neu starten.
## Stolperfallen
- Das Zimmer ist oft dunkel → Belichtung regelt sich in den ersten 1–2 Sekunden ein.
- Handy-Display spiegelt: leicht schräg halten.
Zuletzt geprüft: 25.11.2026
