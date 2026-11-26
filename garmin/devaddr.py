"""Bluetooth-Adresse der Uhr: $GARMIN_ADDR oder Datei garmin/addr (nicht im Repo)."""
import os
from pathlib import Path


def addr():
    a = os.environ.get("GARMIN_ADDR", "").strip()
    if not a:
        f = Path(__file__).resolve().parent / "addr"
        a = f.read_text().strip() if f.exists() else ""
    if not a:
        raise SystemExit("Keine Uhr-Adresse: GARMIN_ADDR setzen oder in garmin/addr eintragen (AA:BB:CC:DD:EE:FF)")
    return a
