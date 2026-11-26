#!/usr/bin/env python3
"""
Sicherheits-Wächter für Jarvis' Gehirn (Claude-Code-Hooks).

Idee: Webinhalte (WebFetch/WebSearch) können versteckte Anweisungen enthalten (Prompt Injection).
Sobald im laufenden Gespräch Webinhalte gelesen wurden, gilt das Gespräch als "tainted".
Dann werden nur Nachrichtenversand und curl|sh blockiert, bis Harry in seiner NÄCHSTEN Nachricht zustimmt.
Unabhängig davon werden echte Zerstörer (rm -rf /, rm *, mkfs, dd auf Geräte …) IMMER gestoppt.
Die Zustimmung gilt nur für diese eine Runde, aber für die ganze Aktionsklasse: Jarvis darf den
Befehl danach leicht umformulieren (z.B. `| head -1` statt `| head -2`), ohne erneut fragen zu müssen.

Zusätzlich (immer aktiv): SPEICHERSCHUTZ für die kleine Systempartition (/, ~2,6 GB).
Nur apk-Installationen, die den freien Platz unter die Reserve drücken würden, werden blockiert.

Härtung:
- FAIL-CLOSED: wirft der Wächter selbst einen Fehler, wird das Werkzeug blockiert (Exit 2), nicht durchgelassen.
- FREIGABE GEBUNDEN: Harrys Ja gibt die zuletzt blockierten Aktionen frei – pro Aktionsklasse
  (git push, Senden an denselben Empfänger, Upload, Pfad), einmalig pro Runde. Bei Zerstörern bleibt
  die Freigabe bewusst an den exakten Befehl gebunden.
- TAINT zusätzlich: Datenabfluss (curl -d/-F/-T, nc, scp, rsync/ssh nach außen, lange Query-URLs per WebFetch),
  Zugriff auf Zugangsdaten (~/.ssh, Tokens, Credentials) und Persistenz (Shell-Profile, Autostart, cron, /etc).
- WÄCHTER-SCHUTZ (immer): Änderungen an guard.py, brain-settings.json, Git-Hooks, system/ brauchen Harrys Ja.
- VERÖFFENTLICHUNG (immer): git push/remote, --no-verify, core.hooksPath brauchen Harrys Ja.
Grenzen: Das ist eine Heuristik, keine Sandbox. Siehe SECURITY.md.

Aufruf:  guard.py taint | taintmsg | prompt | pre     (Hook-JSON auf stdin)
"""
import json, os, re, sys, time

STATE = '/run/user/%d/jarvis-guard.json' % os.getuid()
HOME = os.path.expanduser('~')
TAINT_TTL = 15 * 60
GRANT_TTL = 10 * 60      # Harrys Ja gilt für die laufende Runde, auch bei leicht geändertem Befehl
ROOT_RESERVE_MB = 250    # so viel muss auf / mindestens frei bleiben (sonst bricht das System)

# KRITISCH: wird IMMER blockiert (auch ohne Webinhalte), bis Harry in seiner nächsten Nachricht Ja sagt.
# Bewusst eng gehalten: nur Dinge, die das System oder große Datenmengen unwiderruflich zerstören.
_TOP = r'(/|/\*|~|~/|~/\*|\$HOME/?|\$HOME/\*|/data/?|/data/\*|/data/home/?|/data/home/\*|/home/?|/home/\w+/?|/home/\w+/\*' \
       r'|~/jarvis/?|/(etc|usr|bin|sbin|lib|lib64|boot|var|opt|root|dev|sys|proc)(/\*?)?|\*|\.\*?|\./\*|\.\./?\*?)'
CRITICAL = re.compile(r'''(?x)
    \brm\s[^;&|]*?(?<=\s)["']?''' + _TOP + r'''["']?(?=\s|$|[;&|])   # rm auf /, ~, /data, Systemordner, *
  | \bfind\s+(/|~|\$HOME|/data)\S*\s[^;&|]*-delete\b
  | \b(mkfs\S*|wipefs|sfdisk|fdisk|parted|cryptsetup\s+luksFormat)\b
  | \bdd\b[^;&|]*\bof=/dev/(?!null\b)
  | \bshred\b
  | >\s*/dev/(sd|mmcblk|nvme|vd)
  | \b(chmod|chown)\s+(-\S*R\S*|--recursive)\s+(\S+\s+)?(/|/(etc|usr|bin|sbin|lib|boot|var|data)/?)(\s|$)
  | :\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:                                          # Forkbomb
''')
# Nur wenn fremde Inhalte (Web/Mail/Chat) gelesen wurden: Abfluss/Fremdcode verhindern (Prompt Injection).
TAINT_DANGER = re.compile(r'''(?x)
    (curl|wget)[^|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b
  | \b(wacli\s+(\S+\s+)*(send|revoke|delete|forward|edit)|tg\s+(send|file)|gog\s+(\S+\s+)*(send|reply|reply-all|forward|fwd|trash|delete|share|autoreply)|himalaya\s+(\S+\s+)*(send|reply|forward))\b
''')
# Befehle, die wirklich fremde Nachrichten-/Mailinhalte in den Kontext holen.
# Senden/Sync allein soll nicht already tainted.setzen und vor allem keine Freigaben wegwischen.
MSG_READ = re.compile(r'''(?x)
    \b( wacli\s+(sync|chats?|messages?|msg|read|show|history|search)
      | tg\s+(get|read|messages?|chat|dialogs)
      | gog\s+(message|thread|read|list)
      | himalaya\s+(message|show|read|list)
      | jarvis-show\s+(\S+\s+)*--preset\s+(mail|chat|whatsapp|briefing) )\b
''', re.I)
# Nur bei Taint: Daten nach außen schicken
EXFIL = re.compile(r"""(?x)
    \b(curl|wget)\b[^;&|]*\s(-d|--data\S*|-F|--form\S*|-T|--upload-file|--post-file|--post-data|--body-file|-X\s*(POST|PUT))\b
  | \b(nc|ncat|netcat|socat|telnet)\b\s
  | \b(scp|sftp)\b\s
  | \brsync\b[^;&|]*\s\S+:
  | \bssh\b\s+(-\S+\s+)*\S+@?\S+\s+\S
  | /dev/(tcp|udp)/
  | \bpython3?\b[^;&|]*-c[^;&|]*\b(urllib|requests|http\.client|socket|smtplib)\b
""")
# Zugangsdaten (bei Taint weder lesen noch anfassen)
SECRETS = re.compile(r"""(?x)
    (~|\$HOME|/home/\w+|/data/home)?/?\.(ssh|gnupg|netrc|git-credentials|password-store)\b
  | \.config/(gog|wacli|himalaya|tg|gh|rclone)\b
  | \.claude/\.credentials | \.claude\.json
  | garmin/(passkey|data|\.?tokens?)
  | /etc/(shadow|gshadow|doas\.conf|sudoers)
  | \bid_(rsa|ed25519|ecdsa)\b
""")
# Persistenz/Autostart (bei Taint nicht schreiben). Nicht jede Erwähnung von ~/jarvis/bin
# ist eine Änderung – `ls ~/jarvis/bin 2>/dev/null` war ein falscher Alarm.
PERSIST = re.compile(r"""(?x)
    (~|\$HOME|/home/\w+|/data/home)/\.(bashrc|profile|ashrc|zshrc|xprofile|xinitrc|config/autostart|ssh/authorized_keys)
  | ^/etc/ | \bcrontab\b\s+(-\S*\s+)*[^-l\s] | \bcrontab\s+-e
""")
# Wächter-Manipulation (immer, auch ohne Taint)
GUARD_FILES = re.compile(r'(hooks/guard\.py|brain-settings\.json|\.claude/settings[\w.]*\.json|tools/git-hooks/|jarvis/system/|^system/|/etc/doas)')
# Veröffentlichen/Hooks umgehen (immer): Jarvis pusht nie ohne Harrys Ja
GIT_PUBLISH = re.compile(r'\bgit\b[^;&|]*\s(push|remote\s+(add|set-url))\b|--no-verify\b|\bcore\.hooksPath\b|\bgh\s+(repo|release|gist)\s+(create|edit|upload)\b')
GUARD_WRITE = re.compile(r'(\bsed\s+(-\S+\s+)*-i|(?<![0-9&])>(?!&)|\btee\b|\bmv\b|\bcp\b|\brm\b|\bchmod\b|\btruncate\b|\bln\b|\bpatch\b|\bgit\s+(checkout|restore|apply))')
NEIN = re.compile(r'^\s*(nein|nee|ne|nicht|stopp?|abbrechen|lass\s+es|warte)\b', re.I)
# Bewusst als re.search über die ganze Antwort (nicht nur Satzanfang): natürlich gesprochene Zustimmung
# kommt selten als blankes "ja" zurück ("du darfst es abschicken", "du hast meine erlaubnis", "ist ok so").
# Sicher genug, weil das nur direkt auf Jarvis' eigene Nachfrage ("brauch dein Ja: ...") hin ausgewertet wird.
YES = re.compile(r'''(?x)
    \b(ja|jawohl|jo|yes|okay|ok|klar|genau|bestätigt|einverstanden|los|passt|
       erlaubt|genehmigt|freigegeben|in\s+ordnung)\b
  | \bmach(e)?\s*(das|es|ruhig)?\s*(bitte)?\b
  | \btu\s+es\b | \bführ(e)?\s+(es|ihn|das)\s+aus\b
  | \bdu\s+(darfst|kannst)\b
  | \b(du\s+hast\s+)?(meine\s+)?(ausdrückliche\s+)?erlaubnis\b
  | \b(schick|sende?|führ)(e|'?s)?\s+(es\s+)?(ruhig\s+)?(so\s+)?(ab|los|aus)\b
''', re.I)

def load():
    try:
        s = json.load(open(STATE))
    except Exception:
        s = {}
    if s.get('tainted') and time.time() - s.get('t', 0) > TAINT_TTL:
        s = {}
    return s

def save(s):
    json.dump(s, open(STATE, 'w'))

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny", "permissionDecisionReason": reason}}))

def free_root_mb():
    st = os.statvfs('/')
    return st.f_bavail * st.f_frsize / 1048576

def storage_check(cmd):
    """Grund zum Blockieren oder None."""
    import subprocess
    free = free_root_mb()
    m = re.search(r'\bapk\s+(?:--\S+\s+)*add\s+([^;&|]+)', cmd)
    if m and not re.search(r'(^|\s)(-s|--simulate)(\s|$)', m.group(1)):
        pkgs = [a for a in m.group(1).split() if not a.startswith('-')]
        try:
            sim = subprocess.run(['apk', 'add', '-s', *pkgs], capture_output=True, text=True, timeout=60).stdout
            after = float(re.findall(r'OK: ([\d.]+) MiB', sim)[-1])
            now = int(re.search(r'bytes: (\d+)', subprocess.run(['apk', 'stats'], capture_output=True, text=True,
                                                                timeout=20).stdout).group(1)) / 1048576
            delta = after - now
        except Exception:
            delta = None
        if delta is not None and free - delta < ROOT_RESERVE_MB:
            size = 'ca. %d MB' % delta
            return ('SPEICHERSCHUTZ: Die Installation von %s braucht %s auf der kleinen Systempartition '
                    '(frei: %d MB, Reserve: %d MB). Installiere große Werkzeuge stattdessen auf /data '
                    '(z.B. offizielles Archiv nach /data/home/opt entpacken, pip --user, npm mit Prefix auf /data). '
                    'Wenn es wirklich ein Systempaket sein muss: sag Harry Name und Größe und frage um Erlaubnis.'
                    % (' '.join(pkgs), size, free, ROOT_RESERVE_MB))
    if free < ROOT_RESERVE_MB and re.search(r'\b(apk\s+add|curl\s.*-o\s*/(usr|opt|var|tmp)|wget\s.*-P\s*/(usr|opt|var|tmp))', cmd):
        return 'SPEICHERSCHUTZ: Auf der Systempartition sind nur noch %d MB frei. Lege Dateien auf /data ab.' % free
    return None

def norm_cmd(cmd):
    """Unscheinbare Unterschiede zwischen zwei Versuchen desselben Befehls ignorieren."""
    c = re.sub(r'\b[12]>\s*/dev/null\b', ' ', cmd)
    c = re.sub(r'\b[12]>&\d+\b', ' ', c)
    c = re.sub(r'\|\s*(head|tail)(\s+-\S+)*', ' ', c)
    return re.sub(r'\s+', ' ', c).strip()


def classify(tool, inp):
    """Aktionsklasse für die Freigabe – stabil, auch wenn Jarvis den Befehl umformuliert."""
    cmd = inp.get('command', '') or ''
    path = inp.get('file_path', '') or inp.get('notebook_path', '') or ''
    if tool == 'Bash':
        if GIT_PUBLISH.search(cmd):
            return 'git-publish'
        if re.search(r'\b(wacli|tg|gog|himalaya)\b[^;&|]*\b(send|reply|forward|fwd|file)\b', cmd, re.I):
            m = re.search(r'(?:--to|-t|--chat|--recipient)\s+["\']?([^\s"\';|]+)', cmd)
            return 'send:' + (m.group(1) if m else 'any')
        if re.search(r'(curl|wget)[^|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b', cmd):
            return 'remote-exec'
        if CRITICAL.search(cmd):
            return 'critical:' + norm_cmd(cmd)
        if EXFIL.search(cmd):
            return 'exfil'
        if SECRETS.search(cmd):
            return 'secret'
        if PERSIST.search(cmd):
            return 'persist'
        return 'bash:' + norm_cmd(cmd)
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        return 'write:' + path.replace(HOME, '~')
    if tool == 'Read':
        return 'read:' + path.replace(HOME, '~')
    if tool == 'WebFetch':
        return 'web:' + (inp.get('url', '') or '')
    return tool


def _key(tool, inp):
    """Was genau freigegeben wird: Befehl bzw. Pfad/URL (Redirects/head ignorieren)."""
    if tool == 'Bash':
        return 'Bash:' + norm_cmd(inp.get('command', '') or '')
    return '%s:%s' % (tool, inp.get('file_path') or inp.get('notebook_path') or inp.get('url') or '')


def _pending(s):
    """Pending-Einträge – alte State-Dateien mit reinen Strings werden mitgelesen."""
    out = []
    for e in s.get('pending', []):
        if isinstance(e, dict):
            out.append(e)
            continue
        tool, _, val = e.partition(':')
        if tool == 'Bash':
            out.append({'key': 'Bash:' + norm_cmd(val), 'cat': classify('Bash', {'command': val})})
        else:
            out.append({'key': e, 'cat': classify(tool, {'file_path': val, 'url': val})})
    return out


def check_pre(tool, inp, s):
    """Grund zum Blockieren oder None."""
    tainted = s.get('tainted')
    cmd = inp.get('command', '') or ''
    path = inp.get('file_path', '') or inp.get('notebook_path', '') or ''
    path_n = path.replace(HOME, '~')
    if tool == 'Bash':
        why = storage_check(cmd)
        if why:
            return why
        if CRITICAL.search(cmd):
            return ("KRITISCHER BEFEHL gestoppt (unwiderruflich destruktiv). Sag Harry in einem Satz, was genau du "
                    "ausführen willst. Erst nach seinem Ja ist genau dieser Befehl freigegeben.")
        if GUARD_FILES.search(cmd) and GUARD_WRITE.search(cmd):
            return "WÄCHTER-SCHUTZ: Änderungen an Wächter/Hook-Konfiguration brauchen Harrys Ja (genau dieser Befehl)."
        if GIT_PUBLISH.search(cmd):
            return ("VERÖFFENTLICHUNG: git push/remote, --no-verify, core.hooksPath und gh-Veröffentlichungen brauchen "
                    "Harrys Ja (öffentliches Repo). Sag ihm kurz, was wohin gepusht wird.")
        if tainted:
            if TAINT_DANGER.search(cmd):
                return ("SICHERHEITSSPERRE: Es wurden fremde Inhalte (Web/Mail/Chat) gelesen. Senden von Nachrichten bzw. "
                        "curl|sh braucht Harrys Ja. Sag ihm kurz Empfänger/Befehl.")
            if EXFIL.search(cmd):
                return ("SICHERHEITSSPERRE (Datenabfluss): Nach fremden Inhalten werden Uploads/Verbindungen nach außen "
                        "(curl -d/-F/-T, nc, scp, rsync, ssh-Befehle) nur mit Harrys Ja ausgeführt. Sag ihm Ziel und Zweck.")
            if SECRETS.search(cmd):
                return "SICHERHEITSSPERRE: Nach fremden Inhalten kein Zugriff auf Zugangsdaten/Schlüssel ohne Harrys Ja."
            if PERSIST.search(cmd) and re.search(r'(>|\btee\b|\bsed\s+-i|\bcp\b|\bmv\b|\bln\b|crontab)', cmd):
                return "SICHERHEITSSPERRE: Nach fremden Inhalten keine Änderungen an Autostart/Profilen/System ohne Harrys Ja."
        return None
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        if GUARD_FILES.search(path):
            return "WÄCHTER-SCHUTZ: Änderungen an %s brauchen Harrys Ja." % path_n
        if tainted and (SECRETS.search(path_n) or PERSIST.search(path_n) or PERSIST.search(path)):
            return "SICHERHEITSSPERRE: Nach fremden Inhalten kein Schreiben nach %s ohne Harrys Ja." % path_n
        return None
    if tool == 'Read':
        if tainted and SECRETS.search(path_n):
            return "SICHERHEITSSPERRE: Nach fremden Inhalten kein Lesen von Zugangsdaten (%s) ohne Harrys Ja." % path_n
        return None
    if tool == 'WebFetch':
        url = inp.get('url', '') or ''
        q = url.split('?', 1)[1] if '?' in url else ''
        if tainted and (len(q) > 150 or re.search(r'[A-Za-z0-9+/_=-]{80,}', url)):
            return "SICHERHEITSSPERRE: Nach fremden Inhalten keine URLs mit langen Daten-Anhängseln (möglicher Abfluss)."
        return None
    return None


def main():
    mode = sys.argv[1]
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    s = load()
    sid = data.get('session_id', '')
    if s.get('sid') and s.get('sid') != sid:
        s = {}              # neues Gehirn = neuer, sauberer Kontext
    s['sid'] = sid

    if mode == 'taint':
        # Neue fremde Inhalte verlängern den Taint, dürfen aber eine bereits erteilte
        # Freigabe nicht wegwischen (sonst scheitert jeder zweite Versuch erneut).
        s['tainted'] = True; s['t'] = time.time()
        save(s); return

    if mode == 'taintmsg':
        # Nur echtes Lesen fremder Inhalte setzt Taint – und nur einmal pro Runde.
        ti = data.get('tool_input', {}) or {}
        cmd = ti.get('command', '') or ''
        fp = ti.get('file_path', '') or ''
        if not s.get('tainted') and (MSG_READ.search(cmd) or '/jarvis/research' in cmd
                                     or 'jarvis-research --show' in cmd or '/jarvis/research/' in fp):
            s['tainted'] = True; s['t'] = time.time()
            save(s)
        return

    if mode == 'prompt':
        text = data.get('prompt', '')
        body = text.split('\n', 1)[1] if text.startswith('[Kontext:') and '\n' in text else text
        body = body.replace('[getippt]', '').strip()
        from_harry = 'Quelle: Sprache' in text or 'Quelle: getippt' in text
        # Ja gilt nur für das, was zuletzt blockiert wurde – nicht pauschal. "nicht" an beliebiger Stelle
        # sperrt zusätzlich zu NEIN, sonst würde "mach das nicht" über "mach das" fälschlich als Ja zählen.
        negated = NEIN.search(body) or re.search(r'\bnicht\b', body, re.I)
        consents = from_harry and not negated and YES.search(body)
        entries = _pending(s) if consents else []
        s['granted'] = [e['key'] for e in entries]
        # Zerstörer bleiben an den exakten Befehl gebunden, alles andere an die Aktionsklasse.
        s['granted_cats'] = [e['cat'] for e in entries if not e['cat'].startswith('critical:')]
        s['grant_t'] = time.time() if consents else 0
        s['pending'] = []
        save(s); return

    if mode == 'pre':
        tool = data.get('tool_name', '')
        inp = data.get('tool_input', {}) or {}
        key = _key(tool, inp)
        cat = classify(tool, inp)
        if key in s.get('granted', []):
            s['granted'].remove(key); save(s)
            return
        if cat in s.get('granted_cats', []) and time.time() - s.get('grant_t', 0) <= GRANT_TTL:
            return
        why = check_pre(tool, inp, s)
        if why:
            pending = _pending(s)
            if not any(e['key'] == key for e in pending):
                pending = (pending + [{'key': key, 'cat': cat}])[-5:]
            s['pending'] = pending
            save(s)
            deny(why)
        return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                       # fail-closed: lieber blockieren als durchlassen
        if len(sys.argv) > 1 and sys.argv[1] == 'pre':
            print('Wächter-Fehler (%s) – Aktion vorsorglich blockiert.' % e, file=sys.stderr)
            sys.exit(2)
