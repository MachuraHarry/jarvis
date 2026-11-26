#!/bin/sh
# Installiert die Root-Schnittstelle. Aufruf (als harry): doas sh system/install.sh [--activate]
#   ohne --activate: nur Helfer + nmap-Capabilities (nichts an doas geändert)
#   --activate:      zusätzlich doas-Regel (danach Root nur noch mit Passwort, außer jarvis-root)
set -eu
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo "bitte mit doas starten"; exit 1; }
install -d -o root -g root -m 0755 /usr/local/libexec /usr/local/libexec/jarvis
install -o root -g root -m 0755 jarvis-root /usr/local/libexec/jarvis/jarvis-root
# nmap ohne Root (Raw-Sockets per Capability, Aufruf mit --privileged)
command -v setcap >/dev/null && setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip "$(command -v nmap)" || true
if [ "${1:-}" = --activate ]; then
  install -o root -g root -m 0600 doas-jarvis.conf /etc/doas.d/99-jarvis.conf.new
  doas -C /etc/doas.d/99-jarvis.conf.new && mv /etc/doas.d/99-jarvis.conf.new /etc/doas.d/99-jarvis.conf \
    || { rm -f /etc/doas.d/99-jarvis.conf.new; echo "doas-Regel ungültig – nichts geändert"; exit 1; }
  echo "doas-Regel aktiv. Rückgängig: doas rm /etc/doas.d/99-jarvis.conf"
fi
echo "OK"
