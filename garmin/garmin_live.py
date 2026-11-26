#!/usr/bin/env python3
"""Live-Daemon fenix 5 Plus -> /run/user/<uid>/jarvis-watch.json

Hält eine BLE-Verbindung (Multi-Link), registriert die Echtzeit-Dienste der Uhr
und schreibt den aktuellen Stand ca. 1×/s atomar als JSON. Jarvis liest die
Datei in seiner Telemetrie-Schleife und schickt sie als 'watch' ans HUD.

Echtzeit-Dienste (empirisch dekodiert, fenix 5 Plus FW 4.80):
   6 HF          b1=Puls, b2=Ruhepuls
   7 Schritte    u32 Schritte, u32 Ziel
   8 Kalorien    u32 gesamt, u32 aktiv
   9 Etagen      u16 hoch, u16 runter, u16 Ziel
  10 Intensität  … u32@6 Wochenminuten, u32@10 Ziel
  12 RR          u16 RR-Intervall [ms], u32 Zeitstempel  -> HRV (RMSSD)
  13 Stress      u16 Stress (0..100, sonst ungültig)
Akku: GFDI 5023 (Battery Status) über garmin-proto-lab.
"""
import asyncio, collections, json, math, os, signal, sys, time
from pathlib import Path

import garmin_proto_lab.transport as T
T.select_gfdi_link = lambda services: (_ for _ in ()).throw(T.TransportError("force multilink"))

from garmin_proto_lab.auth_protocol import AuthProtocolEngine
from garmin_proto_lab.bleak_backend import BleakBackend
from garmin_proto_lab.capabilities import FITNESS_HOST_FLAGS
from garmin_proto_lab.cli import _finish_pairing_state, _prompt_passkey, _wait_until
from garmin_proto_lab.client import GarminClient, SemanticKind
from garmin_proto_lab.handshake import HostIdentity
from garmin_proto_lab.link import GfdiMessageLink
from garmin_proto_lab.session import FilePairingStore, requires_system_bond
from garmin_proto_lab.transport import BleTransport, DiscoveredDevice

ADDR = __import__("devaddr").addr()
STATE = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "jarvis-watch.json"
LOG = Path(__file__).resolve().parent / "live.log"
RT_SERVICES = {6: "hr", 7: "steps", 8: "calories", 9: "floors", 10: "intensity", 12: "rr", 13: "stress"}

state = {"connected": False, "device": "fenix 5 Plus"}
rr_buf = collections.deque(maxlen=120)


def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    try:
        with LOG.open("a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def write_state():
    """Nie werfen: /run/user/<uid> kann beim Sitzungswechsel kurz fehlen."""
    state["ts"] = time.time()
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, STATE)
    except OSError as e:
        log("Statusdatei:", e)


def u16(b, o): return int.from_bytes(b[o:o + 2], "little")
def u32(b, o): return int.from_bytes(b[o:o + 4], "little")


def decode(svc, p):
    now = time.time()
    if svc == 6 and len(p) >= 3:
        if 25 <= p[1] <= 230:
            state["hr"] = p[1]; state["hr_ts"] = now
        if 25 <= p[2] <= 150:
            state["rhr"] = p[2]
    elif svc == 7 and len(p) >= 8:
        state["steps"], state["steps_goal"] = u32(p, 0), u32(p, 4)
    elif svc == 8 and len(p) >= 8:
        state["kcal"], state["kcal_active"] = u32(p, 0), u32(p, 4)
    elif svc == 9 and len(p) >= 6:
        state["floors_up"], state["floors_down"], state["floors_goal"] = u16(p, 0), u16(p, 2), u16(p, 4)
    elif svc == 10 and len(p) >= 14:
        state["intensity_week"], state["intensity_goal"] = u32(p, 6), u32(p, 10)
    elif svc == 12 and len(p) >= 2:
        rr = u16(p, 0)
        if 250 <= rr <= 2000:
            rr_buf.append(rr)
            state["rr"] = rr
            if len(rr_buf) >= 10:
                d = [b - a for a, b in zip(rr_buf, list(rr_buf)[1:])]
                d = [x for x in d if abs(x) < 300]  # Artefakte raus
                if d:
                    state["hrv_rmssd"] = round(math.sqrt(sum(x * x for x in d) / len(d)))
    elif svc == 13 and len(p) >= 2:
        s = u16(p, 0)
        if 0 <= s <= 100:
            state["stress"] = s


async def session():
    backend = BleakBackend(assume_bonded=True)
    store = FilePairingStore(str(Path.home() / ".local/share/garmin-proto/pairing.json"))
    transport = BleTransport(backend, require_bond=requires_system_bond(store, ADDR, force=False, force_garmin_auth=False))
    link = GfdiMessageLink(transport, request_timeout=30)
    auth = AuthProtocolEngine(link, ADDR, store, passkey_provider=_prompt_passkey)
    client = GarminClient(link, HostIdentity(1, "Jarvis", "Jarvis HUD", "Python GFDI client"),
                          FITNESS_HOST_FLAGS, auth=auth)
    tasks = []
    try:
        await client.connect(DiscoveredDevice(ADDR))
        await _wait_until(lambda: client.handshake.complete, 45, "GFDI handshake")
        await _finish_pairing_state(auth, transport, backend, 45)
        try:
            await client.sync_time()
        except Exception as e:
            log("Zeit:", e)
        for ev in (4, 6, 8):  # PAIR_COMPLETE, HOST_FOREGROUND, SYNC_READY
            try:
                await client.link.request(5030, bytes([ev, 0]), timeout=10)
            except Exception:
                pass
        ml = transport.multilink_client
        handles = {}
        for svc in RT_SERVICES:
            try:
                r = await ml.register_service(svc, request_reliable=False)
                if r.handle is not None and int(r.status) == 0:
                    handles[r.handle] = svc
            except Exception as e:
                log(f"Dienst {svc}:", e)
        log("verbunden, Echtzeit-Dienste:", sorted(RT_SERVICES[s] for s in handles.values()))
        state["connected"] = True
        write_state()

        async def reader(h, svc):
            while True:
                try:
                    raw = await ml.recv_raw(h, timeout=3600)
                except Exception:
                    continue
                decode(svc, raw[1:])

        async def events():
            while True:
                ev = await client.events.get()
                if ev.kind == SemanticKind.BATTERY:
                    state["battery"] = ev.value.capacity_percent
                    st = ev.value.state
                    state["battery_state"] = st.name.lower() if st else None
                    log("Akku:", ev.value)

        tasks = [asyncio.create_task(reader(h, s)) for h, s in handles.items()]
        tasks.append(asyncio.create_task(events()))
        while True:
            await asyncio.sleep(1)
            if getattr(transport.state, "value", "") in ("failed", "finished"):
                raise ConnectionError("BLE getrennt")
            if state.get("hr_ts") and time.time() - state["hr_ts"] > 30:
                raise ConnectionError("seit 30 s keine Daten")
            write_state()
    finally:
        for t in tasks:
            t.cancel()
        state["connected"] = False
        write_state()
        try:
            await client.disconnect()
        except Exception:
            pass


async def main():
    backoff = 5
    while True:
        t0 = time.time()
        try:
            await session()
        except asyncio.CancelledError:
            raise
        except BaseException as e:
            log("Verbindung weg:", type(e).__name__, str(e)[:200])
        if time.time() - t0 > 60:
            backoff = 5
        log(f"neuer Versuch in {backoff}s")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 120)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        state["connected"] = False
        write_state()
