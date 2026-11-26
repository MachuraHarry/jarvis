#!/usr/bin/env python3
"""Gehirn-Backends für J.A.R.V.I.S.

Reine Daten/Protokoll-Helfer ohne GTK-, Audio- oder Netzabhängigkeit, damit sie
auch im Selbsttest laufen. Zwei Backends:

  claude    – `claude -p` (stream-json), mit Sicherheits-Hooks, Default
  opencode  – `opencode run --format json`, z. B. Big Pickle (kostenlos, aber
              Kontingent und ohne Fein-Streaming)
"""
import re

BACKENDS = {
    'claude': {
        'label': 'Claude',
        'models': {
            'haiku': 'Claude Haiku – schnell',
            'sonnet': 'Claude Sonnet – ausgewogen',
            'opus': 'Claude Opus – am stärksten',
        },
    },
    'opencode': {
        'label': 'OpenCode',
        'models': {
            'opencode/big-pickle': 'Big Pickle – kostenlos',
        },
    },
}

DEFAULT_BACKEND = 'claude'
DEFAULT_MODEL = 'haiku'

# OpenCode meldet ein erschöpftes Free-Kontingent je nach Version leicht anders.
QUOTA_RE = re.compile(
    r'free[ -](?:usage|limit)|usagelimiterror|usage limit reached|rate limit exceeded|kontingent', re.I)


def normalize(backend, model):
    """(backend, model) validieren und auf erlaubte Werte zurückführen."""
    backend = str(backend or DEFAULT_BACKEND).strip().lower()
    if backend not in BACKENDS:
        backend = DEFAULT_BACKEND
    models = BACKENDS[backend]['models']
    model = str(model or '').strip()
    if model not in models:
        model = DEFAULT_MODEL if backend == 'claude' else next(iter(models))
    return backend, model


def label(backend, model):
    """Kurzes Label für die Statusleiste."""
    backend, model = normalize(backend, model)
    if backend == 'claude':
        return model.upper()[:6]
    return model.split('/')[-1].split('-')[0].upper()[:6]


def quota_error(text):
    """True, wenn OpenCode meldet, dass das Free-Kontingent aufgebraucht ist."""
    return bool(QUOTA_RE.search(str(text or '')))


def parse_event(event):
    """OpenCode-JSON-Zeile -> einheitliches Ereignis für das Jarvis-Gehirn.

    Liefert {'kind': 'delta'|'tool'|'error'|'none', ...}.
    """
    if not isinstance(event, dict):
        return {'kind': 'none'}
    typ = event.get('type')
    part = event.get('part') or {}
    if typ == 'text':
        return {'kind': 'delta', 'text': str(part.get('text') or '')}
    if typ == 'tool_use':
        state = part.get('state') or {}
        return {
            'kind': 'tool',
            'id': str(part.get('id') or part.get('tool') or ''),
            'name': str(part.get('tool') or ''),
            'input': state.get('input') or {},
            'output': state.get('output') or '',
            'error': str(state.get('status') or '').lower() == 'error',
        }
    if typ == 'error':
        err = event.get('error')
        if isinstance(err, dict):
            err = err.get('message') or err.get('type') or err
        return {'kind': 'error', 'text': str(err or event.get('message') or event)}
    return {'kind': 'none'}


def agent_file_text(persona):
    """Generiert eine OpenCode-Agent-Datei, deren System-Prompt die Persona ist."""
    return ('---\n'
            'description: J.A.R.V.I.S. – deutscher Sprachassistent\n'
            'mode: primary\n'
            '---\n\n' + str(persona) + '\n')
