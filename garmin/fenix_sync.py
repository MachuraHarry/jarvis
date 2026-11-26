#!/usr/bin/env python3
"""Direkter BLE-Abzug aller FIT-Dateien von der fenix 5 Plus (nur lesen, nie archivieren).

Nutzt garmin-proto-lab als Protokoll-Stack, erzwingt Multi-Link (Legacy-GFDI
antwortet auf der fenix 5 Plus nicht) und liest das komplette Verzeichnis
(Filter NO_FILTER) inkl. bereits von Garmin Connect archivierter Dateien.

  fenix_sync.py [--list] [--limit N] [--types 4,15,32,49] [--addr AA:BB:..]
"""
import argparse, asyncio, datetime as dt, json, sys
from pathlib import Path

import garmin_proto_lab.transport as T
T.select_gfdi_link = lambda services: (_ for _ in ()).throw(T.TransportError("force multilink"))

from garmin_proto_lab.auth_protocol import AuthProtocolEngine
from garmin_proto_lab.bleak_backend import BleakBackend
from garmin_proto_lab.capabilities import FITNESS_HOST_FLAGS
from garmin_proto_lab.cli import _finish_pairing_state, _prompt_passkey, _wait_until
from garmin_proto_lab.client import GarminClient
from garmin_proto_lab.filetransfer import DirectoryFilter, DirectoryFileFlag
from garmin_proto_lab.handshake import HostIdentity
from garmin_proto_lab.link import GfdiMessageLink
from garmin_proto_lab.session import FilePairingStore, requires_system_bond
from garmin_proto_lab.transport import BleTransport, DiscoveredDevice

BASE = Path(__file__).resolve().parent
OUT = BASE / "data" / "fit"
GARMIN_EPOCH = dt.datetime(1989, 12, 31, tzinfo=dt.timezone.utc)
FIT_SUBTYPES = {4: "activity", 15: "monitoring", 32: "monitoring_b", 49: "sleep", 44: "segment",
                34: "segment_list", 41: "hrv?", 28: "totals", 29: "goals", 1: "device", 2: "settings",
                3: "sport", 5: "workout", 6: "course", 7: "schedules", 9: "weight", 10: "totals",
                54: "records?", 58: "metrics?", 68: "?"}


def ts(t):
    return (GARMIN_EPOCH + dt.timedelta(seconds=t)).astimezone() if t else None


async def run(a):
    backend = BleakBackend(assume_bonded=True)
    store = FilePairingStore(str(Path.home() / ".local/share/garmin-proto/pairing.json"))
    transport = BleTransport(backend, require_bond=requires_system_bond(store, a.addr, force=False, force_garmin_auth=False))
    link = GfdiMessageLink(transport, request_timeout=a.timeout)
    auth = AuthProtocolEngine(link, a.addr, store, passkey_provider=_prompt_passkey)
    client = GarminClient(link, HostIdentity(1, "Independent Garmin Client", "Independent interoperability lab", "Python GFDI client"),
                          FITNESS_HOST_FLAGS, auth=auth)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        print("verbinde …", flush=True)
        await client.connect(DiscoveredDevice(a.addr))
        await _wait_until(lambda: client.handshake.complete, a.timeout, "GFDI handshake")
        await _finish_pairing_state(auth, transport, backend, a.timeout)
        print("GFDI ok, Init-Sequenz (Zeit, PAIR_COMPLETE, SYNC_READY) …", flush=True)
        try:
            await client.sync_time()
            print("  Zeit gesetzt", flush=True)
        except Exception as e:
            print("  Zeit:", type(e).__name__, e, flush=True)
        # Gadgetbridge GarminSystemEventType: PAIR_START=3, PAIR_COMPLETE=4,
        # SYNC_READY=8, SETUP_WIZARD_COMPLETE=14, HOST_DID_ENTER_FOREGROUND=6
        for ev, name in ((3, "PAIR_START"), (4, "PAIR_COMPLETE"), (14, "SETUP_WIZARD_COMPLETE"),
                         (6, "HOST_FOREGROUND"), (8, "SYNC_READY")):
            try:
                await client.link.request(5030, bytes([ev, 0]), timeout=10)
                print(f"  {name} ack", flush=True)
            except Exception as e:
                print(f"  {name}: {type(e).__name__} {e}", flush=True)
        await asyncio.sleep(3)
        print("lese Verzeichnis …", flush=True)
        listing = await client.list_files(DirectoryFilter(a.filter))

        rows = []
        for it in listing.files:
            e = it.entry
            rows.append({"index": e.file_index, "data_type": e.data_type, "subtype": e.subtype,
                         "kind": FIT_SUBTYPES.get(e.subtype, it.type_name or "?"), "size": e.size,
                         "time": ts(e.timestamp).isoformat() if ts(e.timestamp) else None,
                         "readable": bool(e.flags & DirectoryFileFlag.READ),
                         "archived": bool(e.flags & DirectoryFileFlag.ARCHIVE)})
        (BASE / "data" / "directory.json").write_text(json.dumps(rows, indent=1))
        from collections import Counter
        print(f"{len(rows)} Dateien auf der Uhr:", dict(Counter(r["kind"] for r in rows)), flush=True)

        want = [r for r in rows if r["readable"] and r["data_type"] == 128
                and (not a.types or r["subtype"] in a.types)]
        want.sort(key=lambda r: r["time"] or "", reverse=True)
        if a.list:
            for r in want[: a.limit or None]:
                print(f'  #{r["index"]:<5} {r["kind"]:<13} {r["time"]}  {r["size"]:>8} B {"(arch)" if r["archived"] else ""}')
            return
        n = 0
        for r in want:
            if a.limit and n >= a.limit:
                break
            stamp = (r["time"] or "notime")[:19].replace(":", "")
            dst = OUT / f'{stamp}_{r["kind"]}_{r["index"]}.fit'
            if dst.exists():
                continue
            print(f'  lade #{r["index"]} {r["kind"]} {r["time"]} ({r["size"]} B) …', end="", flush=True)
            try:
                res = await client.read_file(r["index"], compression=False)
                dst.write_bytes(res.data)
                print(f' ok {len(res.data)} B in {res.elapsed_seconds:.1f}s', flush=True)
                n += 1
            except Exception as e:
                print(f" FEHLER {type(e).__name__}: {e}", flush=True)
        print(f"fertig: {n} neue Dateien in {OUT}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--addr", default=None)
    p.add_argument("--list", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--types", type=lambda s: {int(x) for x in s.split(",")}, default=None)
    p.add_argument("--timeout", type=float, default=60)
    p.add_argument("--filter", type=int, default=0, help="Verzeichnisfilter 0=alle 1=default 3=pending")
    a = p.parse_args()
    a.addr = a.addr or __import__("devaddr").addr()
    asyncio.run(run(a))


if __name__ == "__main__":
    main()
