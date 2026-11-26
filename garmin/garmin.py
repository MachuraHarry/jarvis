#!/usr/bin/env python3
"""Garmin-Datenabzug für Jarvis (fenix 5 Plus).

  login                 interaktiv, Tokens -> ~/.garminconnect (ca. 1 Jahr gültig)
  dump [--days N]       Tageswerte (Wellness) als JSON -> data/daily/YYYY-MM-DD.json
  activities [--limit N] [--fit]   Aktivitätsliste + optional Original-FIT-Dateien
  summary               kompakte Tageszusammenfassung (für Jarvis-Prompts)
  hr-live               Live-Puls per BLE (Uhr: Einstellungen > Sensoren > HF übertragen)
  usb PATH              FIT-Dateien von per USB gemounteter Uhr parsen
"""
import argparse, asyncio, datetime as dt, getpass, io, json, os, sys, zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
TOKENS = os.path.expanduser("~/.garminconnect")

# Tageswerte: name -> (methode, nimmt_datum)
DAILY = {
    "stats": "get_stats",
    "heart_rates": "get_heart_rates",
    "sleep": "get_sleep_data",
    "stress": "get_stress_data",
    "respiration": "get_respiration_data",
    "spo2": "get_spo2_data",
    "hrv": "get_hrv_data",
    "steps": "get_steps_data",
    "floors": "get_floors",
    "intensity": "get_intensity_minutes_data",
    "hydration": "get_hydration_data",
    "training_status": "get_training_status",
    "training_readiness": "get_training_readiness",
    "max_metrics": "get_max_metrics",
    "rhr": "get_rhr_day",
    "body_comp": "get_body_composition",
}


def client():
    from garminconnect import Garmin
    g = Garmin()
    try:
        g.login(TOKENS)
    except Exception as e:
        sys.exit(f"Nicht eingeloggt ({e.__class__.__name__}). Erst: jarvis-garmin login")
    return g


def cmd_login(a):
    from garminconnect import Garmin
    email = input("Garmin-E-Mail: ").strip()
    pw = getpass.getpass("Passwort: ")
    g = Garmin(email, pw, prompt_mfa=lambda: input("MFA-Code: ").strip())
    os.makedirs(TOKENS, mode=0o700, exist_ok=True)
    g.login(TOKENS)  # fällt ohne gültige Tokens auf Credentials zurück und speichert sie
    os.chmod(TOKENS, 0o700)
    print(f"OK, eingeloggt als {g.get_full_name()}. Tokens in {TOKENS}")
    for d in g.get_devices() or []:
        print(" Gerät:", d.get("productDisplayName") or d.get("displayName"), d.get("deviceId"))


def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        return {"_error": f"{e.__class__.__name__}: {str(e)[:200]}"}


def cmd_dump(a):
    g = client()
    out = DATA / "daily"; out.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    for i in range(a.days):
        d = (today - dt.timedelta(days=i)).isoformat()
        f = out / f"{d}.json"
        if f.exists() and i > 1 and not a.force:  # alte Tage nicht neu holen
            continue
        rec = {"date": d}
        for k, m in DAILY.items():
            rec[k] = safe(getattr(g, m), d)
        rec["body_battery"] = safe(g.get_body_battery, d, d)
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        errs = [k for k, v in rec.items() if isinstance(v, dict) and "_error" in v]
        print(d, "ok" if not errs else f"ok (fehlend: {', '.join(errs)})")
    for k, m in [("devices", "get_devices"), ("profile", "get_user_profile"),
                 ("personal_records", "get_personal_record"), ("lifetime", "get_lifetime_totals"),
                 ("hr_zones", "get_heart_rate_zones")]:
        (DATA / f"{k}.json").write_text(json.dumps(safe(getattr(g, m)), ensure_ascii=False, indent=1))


def cmd_activities(a):
    g = client()
    out = DATA / "activities"; out.mkdir(parents=True, exist_ok=True)
    acts = g.get_activities(0, a.limit)
    (DATA / "activities.json").write_text(json.dumps(acts, ensure_ascii=False, indent=1))
    for x in acts:
        aid = x["activityId"]
        print(f'{x["startTimeLocal"]}  {x["activityType"]["typeKey"]:<18} '
              f'{(x.get("distance") or 0)/1000:6.2f} km  {(x.get("duration") or 0)/60:6.1f} min  '
              f'HF⌀ {x.get("averageHR") or "-"}  id={aid}')
        fit = out / f"{aid}.fit"
        if a.fit and not fit.exists():
            raw = g.download_activity(aid, dl_fmt=g.ActivityDownloadFormat.ORIGINAL)
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                name = next(n for n in z.namelist() if n.lower().endswith(".fit"))
                fit.write_bytes(z.read(name))


def cmd_summary(a):
    g = client()
    d = (dt.date.today() - dt.timedelta(days=a.offset)).isoformat()
    s = safe(g.get_stats, d)
    sl = safe(g.get_sleep_data, d).get("dailySleepDTO", {}) or {}
    h = lambda sec: f"{(sec or 0)//3600}h{((sec or 0)%3600)//60:02d}"
    print(f"Datum {d}")
    print(f" Schritte {s.get('totalSteps')} / Ziel {s.get('dailyStepGoal')}, Etagen {s.get('floorsAscended')}")
    print(f" Ruhepuls {s.get('restingHeartRate')}, HF min/max {s.get('minHeartRate')}/{s.get('maxHeartRate')}")
    print(f" Stress ⌀ {s.get('averageStressLevel')}, Body Battery {s.get('bodyBatteryMostRecentValue')}")
    print(f" Kalorien {s.get('totalKilocalories')}, Intensitätsmin {s.get('moderateIntensityMinutes')}+{s.get('vigorousIntensityMinutes')}×2")
    print(f" Schlaf {h(sl.get('sleepTimeSeconds'))} (tief {h(sl.get('deepSleepSeconds'))}, "
          f"leicht {h(sl.get('lightSleepSeconds'))}, REM {h(sl.get('remSleepSeconds'))}, wach {h(sl.get('awakeSleepSeconds'))})")


def cmd_hr_live(a):
    st = Path(f"/run/user/{os.getuid()}/jarvis-watch.json")
    if st.exists():
        try:
            w = json.loads(st.read_text())
            if w.get("connected"):
                print("jarvis-watch hält die Uhr bereits verbunden. Live-Werte:")
                print(json.dumps(w, ensure_ascii=False))
                return
        except Exception:
            pass
    from bleak import BleakScanner, BleakClient
    HR_SVC = "0000180d-0000-1000-8000-00805f9b34fb"
    HR_MEAS = "00002a37-0000-1000-8000-00805f9b34fb"

    async def run():
        print("Suche HF-Broadcast …")
        dev = await BleakScanner.find_device_by_filter(
            lambda d, ad: HR_SVC in (ad.service_uuids or []) or "fenix" in (d.name or "").lower(),
            timeout=a.timeout)
        if not dev:
            sys.exit("Nichts gefunden. An der Uhr: Einstellungen > Sensoren & Zubehör > Handgelenk-HF > HF übertragen")
        print("Verbunden mit", dev.name, dev.address)

        def on(_, b: bytearray):
            flags = b[0]
            hr = int.from_bytes(b[1:3], "little") if flags & 1 else b[1]
            i = 3 if flags & 1 else 2
            if flags & 0x08: i += 2
            rr = [int.from_bytes(b[j:j+2], "little") / 1024 for j in range(i, len(b) - 1, 2)] if flags & 0x10 else []
            line = {"t": dt.datetime.now().isoformat(timespec="seconds"), "hr": hr}
            if rr: line["rr"] = [round(x, 3) for x in rr]
            print(json.dumps(line), flush=True)

        async with BleakClient(dev) as c:
            await c.start_notify(HR_MEAS, on)
            while c.is_connected:
                await asyncio.sleep(1)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


def cmd_usb(a):
    from fitparse import FitFile
    root = Path(a.path)
    files = sorted(root.rglob("*.[fF][iI][tT]"))
    out = DATA / "usb"; out.mkdir(parents=True, exist_ok=True)
    for f in files:
        dst = out / f"{f.parent.name}_{f.stem}.json"
        if dst.exists():
            continue
        try:
            msgs = {}
            for m in FitFile(str(f)).get_messages():
                msgs.setdefault(m.name, []).append({k: (str(v) if isinstance(v, (dt.datetime, dt.time)) else v)
                                                     for k, v in m.get_values().items()})
            dst.write_text(json.dumps(msgs, default=str))
            print(f, "->", dst.name, {k: len(v) for k, v in msgs.items() if k in ("record", "session", "monitoring", "lap")})
        except Exception as e:
            print(f, "FEHLER", e)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("login").set_defaults(f=cmd_login)
    x = sp.add_parser("dump"); x.add_argument("--days", type=int, default=7); x.add_argument("--force", action="store_true"); x.set_defaults(f=cmd_dump)
    x = sp.add_parser("activities"); x.add_argument("--limit", type=int, default=20); x.add_argument("--fit", action="store_true"); x.set_defaults(f=cmd_activities)
    x = sp.add_parser("summary"); x.add_argument("--offset", type=int, default=0); x.set_defaults(f=cmd_summary)
    x = sp.add_parser("hr-live"); x.add_argument("--timeout", type=float, default=20); x.set_defaults(f=cmd_hr_live)
    x = sp.add_parser("usb"); x.add_argument("path"); x.set_defaults(f=cmd_usb)
    a = p.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
