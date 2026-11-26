"""
Lokale Grundbefehle – funktionieren ohne Internet und sind sofort da (kein Umweg über Claude).
handle(text) -> (antwort, aktion) oder None, wenn der Satz kein einfacher Grundbefehl ist.
Bewusst strikt (ganzer Satz muss passen), damit komplexere Fragen ans Gehirn gehen.
"""
import re, datetime, subprocess, os

BIN = os.path.expanduser('~/jarvis/bin')

_UNITS = {'null': 0, 'ein': 1, 'eins': 1, 'eine': 1, 'einen': 1, 'einer': 1, 'zwei': 2, 'drei': 3, 'vier': 4,
          'fünf': 5, 'sechs': 6, 'sieben': 7, 'acht': 8, 'neun': 9, 'zehn': 10, 'elf': 11, 'zwölf': 12,
          'dreizehn': 13, 'vierzehn': 14, 'fünfzehn': 15, 'sechzehn': 16, 'siebzehn': 17, 'achtzehn': 18,
          'neunzehn': 19}
_TENS = {'zwanzig': 20, 'dreißig': 30, 'vierzig': 40, 'fünfzig': 50, 'sechzig': 60, 'siebzig': 70,
         'achtzig': 80, 'neunzig': 90}

def num(w):
    """'fünfundzwanzig' -> 25, '40' -> 40, 'hundert' -> 100. None wenn keine Zahl."""
    w = w.lower().strip()
    if w.isdigit():
        return int(w)
    total = 0
    if 'hundert' in w:
        h, w = w.split('hundert', 1)
        total += 100 * (_UNITS.get(h, 0) if h else 1)
        if h and h not in _UNITS:
            return None
        if not w:
            return total
    if w in _UNITS:
        return total + _UNITS[w]
    if w in _TENS:
        return total + _TENS[w]
    if 'und' in w:
        u, t = w.split('und', 1)
        if u in _UNITS and t in _TENS:
            return total + _UNITS[u] + _TENS[t]
    return None

_FILL = re.compile(r'\b(bitte|mal|doch|jarvis|kannst du|könntest du|würdest du|sag mir|mach|stell|stelle|setz|setze|den|die|das|es|ein|eine|einen)\b')

def _norm(t):
    t = t.lower().replace('?', '').replace('.', '').replace(',', '').replace('!', '').strip()
    return re.sub(r'\s+', ' ', _FILL.sub(' ', t)).strip()

def _run(*cmd):
    try:
        return subprocess.run([os.path.join(BIN, cmd[0]), *cmd[1:]], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ''

WD = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
MO = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
UNIT = {'sekunde': 1, 'sekunden': 1, 'minute': 60, 'minuten': 60, 'stunde': 3600, 'stunden': 3600}

def handle(text):
    raw = text.lower().strip()
    t = _norm(text)
    now = datetime.datetime.now()

    if re.fullmatch(r'(wie spät ist|wie spät|wie viel uhr ist|wieviel uhr ist|wie viel uhr haben wir|wieviel uhr haben wir|uhrzeit|wie ist uhrzeit|was ist uhrzeit)', t):
        m = now.minute
        return ('Es ist %d Uhr%s.' % (now.hour, ' %d' % m if m else ''), None)

    if re.fullmatch(r'(welcher tag ist heute|welchen tag haben wir( heute)?|welches datum (ist|haben wir)( heute)?|der wievielte ist heute|den wievielten haben wir( heute)?|datum|was ist heute für tag|was für tag ist heute)', t):
        return ('Heute ist %s, der %d. %s %d.' % (WD[now.weekday()], now.day, MO[now.month - 1], now.year), None)

    if re.fullmatch(r'(ton |musik |lautstärke )?lauter', t):
        return (_run('jarvis-volume', '+15').replace('(stumm: no)', '').strip() + '.', None)
    if re.fullmatch(r'(ton |musik |lautstärke )?leiser', t):
        return (_run('jarvis-volume', '-15').replace('(stumm: no)', '').strip() + '.', None)
    m = re.fullmatch(r'lautstärke (auf )?(\S+)( prozent)?', t)
    if m and num(m.group(2)) is not None:
        return (_run('jarvis-volume', str(min(150, num(m.group(2))))).replace('(stumm: no)', '').strip() + '.', None)
    if re.fullmatch(r'(ton aus|stumm|stummschalten|stumm schalten)', t):
        _run('jarvis-volume', 'mute'); return ('Ton aus.', None)
    if re.fullmatch(r'(ton an|ton wieder an|stummschaltung aus)', t):
        _run('jarvis-volume', 'unmute'); return ('Ton ist wieder an.', None)

    if re.fullmatch(r'(bildschirm )?heller', t):
        return (_run('jarvis-brightness', '+20') + '.', None)
    if re.fullmatch(r'(bildschirm )?dunkler', t):
        return (_run('jarvis-brightness', '-20') + '.', None)
    m = re.fullmatch(r'helligkeit (auf )?(\S+)( prozent)?', t)
    if m and num(m.group(2)) is not None:
        return (_run('jarvis-brightness', str(num(m.group(2)))) + '.', None)

    m = (re.fullmatch(r'timer (?:auf |für |von )?(\S+) (sekunden?|minuten?|stunden?)', t) or
         re.fullmatch(r'(\S+) (sekunden?|minuten?|stunden?) timer', t))
    if m and num(m.group(1)) is not None:
        n, u = num(m.group(1)), m.group(2)
        secs = n * UNIT[u]
        word = {1: 'Sekunde', 60: 'Minute', 3600: 'Stunde'}[UNIT[u]]
        label = '%d %s%s' % (n, word, '' if n == 1 else 'n')
        return ('Timer läuft: %s.' % label, ('timer', secs, 'Harry, dein Timer über %s ist abgelaufen.' % label))

    if re.fullmatch(r'(starte?|beginne?|mach|nimm)? ?(eine |die )?(bildschirm ?aufnahme|aufnahme|bildschirmvideo|video vom bildschirm|bildschirm auf)( starten| beginnen| auf)?', t) \
            and not re.search(r'(stopp|stop|beend|aus)', t):
        return ('Aufnahme läuft.', ('rec', 'start'))
    if re.fullmatch(r'(stopp?e?|beende|halt)? ?(die )?(bildschirm ?aufnahme|aufnahme)( stoppen| beenden| aus| stopp)?', t) \
            and re.search(r'(stopp|stop|beend|aus|halt)', t):
        return ('Aufnahme wird gespeichert.', ('rec', 'stop'))
    return None

OFFLINE = ('Ich bin gerade offline, Harry, mein Verstand braucht eine Internetverbindung. '
           'Uhrzeit, Datum, Lautstärke, Helligkeit und Timer gehen trotzdem.')
