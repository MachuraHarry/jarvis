#!/bin/sh
# Startet Jarvis und startet ihn nach einem Absturz neu – nur solange die grafische Sitzung läuft.
cd "$HOME/jarvis"
export PATH="$HOME/jarvis/bin:$HOME/.local/bin:$PATH"
export DISPLAY="${DISPLAY:-:0}"
# Beim frühen Start existiert /run/user/UID evtl. noch nicht -> kurz warten
R="/run/user/$(id -u)"; i=0
while [ ! -d "$R" ] && [ $i -lt 150 ]; do sleep 0.1; i=$((i+1)); done
# nur ein Wrapper gleichzeitig
exec 9>"/run/user/$(id -u)/jarvis-run.lock"
flock -n 9 || exit 0
# Speicherschutz + CPU-Vorrang (vererbt sich auf alle Jarvis-Prozesse)
"$HOME/jarvis/bin/jarvis-root" prio $$ >/dev/null 2>&1

# Früher Start aus ~/.xprofile: auf xfce4-session warten und deren D-Bus-Sitzung übernehmen
if [ -n "$JARVIS_EARLY" ]; then
  i=0
  while [ $i -lt 100 ]; do
    p=$(pgrep -u "$(id -u)" -x xfce4-session | head -1)
    if [ -n "$p" ]; then
      a=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^DBUS_SESSION_BUS_ADDRESS=' | cut -d= -f2-)
      [ -n "$a" ] && { export DBUS_SESSION_BUS_ADDRESS="$a"; break; }
    fi
    sleep 0.1; i=$((i+1))
  done
  for v in XDG_CURRENT_DESKTOP XDG_SESSION_TYPE XDG_SESSION_ID XDG_SEAT XDG_VTNR; do
    val=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep "^$v=" | cut -d= -f2-)
    [ -n "$val" ] && export "$v=$val"
  done
fi

fails=0; quick=0
while true; do
  # stdout.log begrenzen
  [ -f stdout.log ] && [ "$(stat -c %s stdout.log)" -gt 2000000 ] && mv -f stdout.log stdout.log.old
  t0=$(date +%s)
  python3 app/jarvis.py >> "$HOME/jarvis/stdout.log" 2>&1
  rc=$?
  [ -f "$HOME/jarvis/.stop" ] && { rm -f "$HOME/jarvis/.stop"; exit 0; }
  [ $rc -eq 3 ] && exit 0
  # Crash-Loop: 3x hintereinander nach weniger als 20 s beendet -> Rollback auf den letzten guten Stand (git-Tag "good")
  if [ $(( $(date +%s) - t0 )) -lt 20 ] && [ $rc -ne 0 ]; then quick=$((quick+1)); else quick=0; fi
  if [ $quick -ge 3 ] && git rev-parse -q --verify good >/dev/null 2>&1; then
    bad=$(git rev-parse --short HEAD)
    echo "$(date '+%F %T') run.sh: Crash-Loop (rc=$rc) – Rollback auf good" >> "$HOME/jarvis/restart.log"
    git stash push -q -m "crashloop-$bad" -- app hooks bin 2>/dev/null
    git checkout -q good -- app hooks bin 2>/dev/null
    mkdir -p state
    echo "Ich bin dreimal direkt nach dem Start abgestürzt und habe mich auf den letzten funktionierenden Stand zurückgesetzt. Die kaputten Änderungen liegen im git stash." > state/rollback-notice
    quick=0
  fi
  if ! xset q >/dev/null 2>&1; then
    fails=$((fails+1)); [ $fails -ge 5 ] && exit 0
  else
    fails=0
  fi
  sleep 3
done
