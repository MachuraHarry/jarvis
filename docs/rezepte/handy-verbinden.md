# Handy (Pixel 9) verbinden, steuern und spiegeln
Wann: Harry will etwas auf seinem Handy sehen, zeigen, aufnehmen oder fernsteuern.
## Schritte
1. `jarvis-phone connect` – findet das Handy selbst (mDNS im WLAN, sonst Portscan der letzten IP). Nicht nach IP/Port fragen.
2. Klappt das nicht und das Handy war nie gekoppelt (oder Kopplung verloren): `jarvis-phone pair-qr` starten (läuft bis
   3 Minuten, im Hintergrund mit `&` oder run_in_background) und Harry sagen: "Scann den Code im HUD unter Entwickleroptionen,
   Drahtloses Debugging, Gerät über QR-Code koppeln." Danach verbindet es sich automatisch.
3. Ist drahtloses Debugging am Handy aus, sag Harry genau das (Schnellzugriff: Entwickleroptionen › Drahtloses Debugging).
4. Live-Bild: `jarvis-phone mirror`. Screenshot zum Auswerten: `jarvis-phone shot`, dann Datei mit Read ansehen.
## Befehle
- Tippen/Wischen/Text: `jarvis-phone shell input tap X Y` · `input swipe X1 Y1 X2 Y2 300` · `input text "hallo"`
- URL öffnen: `jarvis-phone shell am start -a android.intent.action.VIEW -d https://...`
- App starten: `jarvis-phone shell monkey -p com.whatsapp 1` · Paketliste: `jarvis-phone shell pm list packages`
- Bildschirmgröße: `jarvis-phone shell wm size` (Pixel 9: 1080x2424)
## Stolperfallen
- Port des drahtlosen Debuggings wechselt bei jedem Einschalten – deshalb immer `connect` statt fester Ports.
- KDE Connect zeigt KEIN Bild, nur Benachrichtigungen/Dateien.
- Vorführungen: Spiegelung starten und Fenster nach vorne holen, bevor du am Handy etwas tust.
Zuletzt geprüft: 25.11.2026
