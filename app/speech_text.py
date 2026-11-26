"""Reine Textfunktionen der Sprachein-/ausgabe (ohne GTK/Audio) – dadurch testbar (tests/selftest.py)."""
import re

# Wörter, die allein (ohne vorherige Rückfrage von Jarvis) fast immer Fehlerkennungen sind
FILLER = set('''der die das den dem des ein eine einen ja jo nein ne und oder was wer wir ihr ist sind war hast hat bis
von vom zu zum zur diese dieser dieses es er sie ich du man so da hier dort ok okay hm hmm äh ähm also gut genau
gemacht macht mal noch schon auch nicht doch wo wie hallo service harry unk'''.split())

WAKE_RE = re.compile(r'^(?:\S+\s+){0,2}?(?:hey |okay |ok )?(?:jarvis|javis|jervis|dschawis|tschawis|scharfes|service|(?:ja|jahr|jah)\s+(?:bis|wies?|wis|wiss|will|willst|wiest))\b[\s,]*')


def clean_text(text):
    t = re.sub(r'```.*?```', ' ', text, flags=re.S)
    t = re.sub(r'https?://\S+', ' Link ', t)
    t = re.sub(r'[*_#`>|~\[\]]', '', t)
    t = re.sub(r'^\s*[-•]\s+', '', t, flags=re.M)
    t = t.replace('°C', ' Grad').replace('°', ' Grad').replace('%', ' Prozent').replace('&', ' und ')
    t = t.replace('J.A.R.V.I.S.', 'Jarvis').replace('z.B.', 'zum Beispiel').replace('ca.', 'circa')
    t = re.sub(r'[\U0001F000-\U0001FFFF☀-➿]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def split_text(text):
    parts = re.split(r'(?<=[.!?;:])\s+', text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # sehr lange Sätze an Kommas teilen -> schnellerer Start
        while len(p) > 180 and ',' in p[60:]:
            i = p.index(',', 60) + 1
            out.append(p[:i]); p = p[i:].strip()
        out.append(p)
    return out

