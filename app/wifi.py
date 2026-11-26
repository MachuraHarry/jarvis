"""
WLAN-Verwaltung über nmcli (NetworkManager). Läuft ohne sudo.
Alle Funktionen blockieren -> aus einem Thread aufrufen.
"""
import re, subprocess

def _nm(*args, timeout=20):
    r = subprocess.run(['nmcli', *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

def _split(line):
    """nmcli -t trennt mit ':' und maskiert ':' im Inhalt als '\\:'."""
    parts = re.split(r'(?<!\\):', line)
    return [p.replace('\\:', ':').replace('\\\\', '\\') for p in parts]

def status():
    """{'radio': bool, 'ssid': str|None, 'signal': int, 'connecting': bool}"""
    try:
        _, radio, _ = _nm('-t', 'radio', 'wifi', timeout=5)
        _, dev, _ = _nm('-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device', timeout=5)
    except Exception:
        return {'radio': True, 'ssid': None, 'signal': 0, 'connecting': False}
    ssid, connecting = None, False
    for l in dev.splitlines():
        d = _split(l)
        if len(d) >= 4 and d[1] == 'wifi':
            if d[2] == 'connected':
                ssid = d[3]
            elif 'connecting' in d[2]:
                connecting = True
    return {'radio': radio.strip() == 'enabled', 'ssid': ssid, 'connecting': connecting}

def saved():
    try:
        _, out, _ = _nm('-t', '-f', 'NAME,TYPE', 'connection', 'show', timeout=5)
    except Exception:
        return set()
    return {_split(l)[0] for l in out.splitlines() if l.endswith(':802-11-wireless')}

def scan(rescan=True):
    """Liste von Netzen, stärkstes Signal pro SSID, sortiert (verbunden zuerst, dann Signal)."""
    try:
        _, out, _ = _nm('-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list',
                        '--rescan', 'yes' if rescan else 'no', timeout=25)
    except Exception:
        out = ''
    known = saved()
    nets = {}
    for l in out.splitlines():
        d = _split(l)
        if len(d) < 4 or not d[1].strip():
            continue                       # versteckte Netze ohne Namen überspringen
        ssid, sig = d[1], int(d[2] or 0)
        sec = d[3].strip()
        cur = nets.get(ssid)
        if cur and cur['signal'] >= sig and not d[0] == '*':
            continue
        nets[ssid] = {'ssid': ssid, 'signal': sig, 'secure': bool(sec) and sec != '--', 'security': sec,
                      'active': d[0] == '*' or (cur or {}).get('active', False), 'saved': ssid in known}
    return sorted(nets.values(), key=lambda n: (not n['active'], not n['saved'], -n['signal']))

def connect(ssid, password=None):
    """Verbindet. Gibt (ok, meldung) zurück."""
    if ssid in saved() and not password:
        code, out, err = _nm('connection', 'up', 'id', ssid, timeout=45)
    elif password:
        # evtl. alte, fehlerhafte Verbindung gleichen Namens entfernen
        if ssid in saved():
            _nm('connection', 'delete', 'id', ssid, timeout=10)
        code, out, err = _nm('device', 'wifi', 'connect', ssid, 'password', password, timeout=45)
    else:
        code, out, err = _nm('device', 'wifi', 'connect', ssid, timeout=45)
    if code == 0:
        return True, 'Verbunden mit %s' % ssid
    msg = (err or out).strip()
    low = msg.lower()
    # nmcli legt die Verbindung auch bei falschem Passwort an -> wieder entfernen
    if password and ssid in saved() and ('secrets' in low or 'password' in low or 'activation failed' in low):
        _nm('connection', 'delete', 'id', ssid, timeout=10)
    if 'secrets were required' in low or 'password' in low or '802-1x' in low:
        return False, 'Passwort falsch oder fehlt.'
    if 'no network with ssid' in low:
        return False, 'Netz nicht gefunden – außer Reichweite?'
    if 'timeout' in low or 'timed out' in low:
        return False, 'Zeitüberschreitung beim Verbinden.'
    return False, msg.replace('Error: ', '')[:160] or 'Verbindung fehlgeschlagen.'

def disconnect():
    _, dev, _ = _nm('-t', '-f', 'DEVICE,TYPE', 'device', timeout=5)
    for l in dev.splitlines():
        d = _split(l)
        if len(d) >= 2 and d[1] == 'wifi':
            code, out, err = _nm('device', 'disconnect', d[0], timeout=15)
            return code == 0, 'Getrennt.' if code == 0 else (err or out).strip()[:160]
    return False, 'Kein WLAN-Gerät gefunden.'

def forget(ssid):
    code, out, err = _nm('connection', 'delete', 'id', ssid, timeout=15)
    return code == 0, ('%s vergessen.' % ssid) if code == 0 else (err or out).strip()[:160]

def radio(on):
    code, out, err = _nm('radio', 'wifi', 'on' if on else 'off', timeout=10)
    return code == 0, ('WLAN eingeschaltet.' if on else 'WLAN ausgeschaltet.') if code == 0 else (err or out).strip()[:160]
