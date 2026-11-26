# Screenshot vom Tablet machen und auf Google Drive laden
Wann: Harry will einen Screenshot des Tablet-Bildschirms, z.B. "mach ein Screenshot und lade es auf mein Google Drive".

Schritte:
1. Ordner anlegen: mkdir -p ~/Pictures/jarvis-screens
2. Aufnahme (Hochformat, 1200x1920, scrot/import/xwd sind NICHT installiert):
   f=~/Pictures/jarvis-screens/screenshot-$(date +%Y%m%d-%H%M%S).png
   DISPLAY=:0 ffmpeg -loglevel error -f x11grab -video_size 1200x1920 -i :0.0 -frames:v 1 -y "$f"
3. Upload: gog drive upload "$f" 2>&1 | tail -8  (gibt id und link aus)
Hinweis: x11grab mit 1920x1200 schlägt fehl, die Bildschirmgröße ist 1200x1920.
