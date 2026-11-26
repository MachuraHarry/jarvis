# Sicherheitscheck des eigenen Heimnetzes
Wann: Harry will wissen, ob sein WLAN/seine Geräte sicher sind, oder sagt "scann mal mein Netz / check meine Sicherheit".
## Schritte
1. `jarvis-pentest netmap` – alle Geräte im WLAN auflisten (eigenes Netz ist freigegeben).
2. Für jedes interessante Gerät (Router, NAS, Kameras, PC): `jarvis-pentest scan <ip>` – offene Dienste/Versionen.
3. Hat ein Gerät Weboberfläche (Port 80/443/8080): `jarvis-pentest web http://<ip>` (Technik + nuclei).
4. Auffällige Dienste genauer prüfen: `jarvis-pentest vulns <ip>`; SMB mit nbtscan/smbclient.py.
5. Ergebnis als klaren Bericht zusammenfassen: pro Gerät was offen ist, welches Risiko, was Harry tun sollte
   (Firmware-Update, Standardpasswort ändern, Port schließen, Dienst abschalten).
## Stolperfallen
- Lange Scans (full, vulns) im Hintergrund starten und Harry sagen, dass die Karte nachkommt.
- Router (192.168.178.1 = Fritzbox) nicht aggressiv bruteforcen – nur prüfen, nicht aussperren.
- Fremde Netze/Geräte brauchen scope-Freigabe.
Zuletzt geprüft: 25.11.2026
