#!/usr/bin/env python3
"""Welche Multi-Link-Dienste nimmt die fenix an? Registriert IDs 2..40 (ohne GFDI) und lauscht."""
import asyncio, sys, time
from bleak import BleakClient

ADDR = sys.argv[1] if len(sys.argv) > 1 else __import__("devaddr").addr()
U = lambda s: f"6a4e{s}-667b-11e3-949a-0800200c9a66"
ML_W, ML_N = U("2820"), U("2810")
CLIENT = (2).to_bytes(8, "little")
t0 = time.time()
handles = {}
pending = {}


def on(_, d: bytearray):
    d = bytes(d)
    if d[0] == 0 and len(d) >= 14 and d[1] == 1:
        svc = int.from_bytes(d[10:12], "little"); st = d[12]; h = d[13] if len(d) > 13 else None
        if st == 0:
            handles[h] = svc
        print(f"{time.time()-t0:6.2f} REG svc={svc:<3} status={st} handle={h:#x}" if st == 0 else
              f"{time.time()-t0:6.2f} REG svc={svc:<3} status={st}", flush=True)
    elif d[0] != 0:
        print(f"{time.time()-t0:6.2f} DATA h={d[0]:#x} svc={handles.get(d[0])} {d[1:].hex(' ')}", flush=True)
    else:
        print(f"{time.time()-t0:6.2f} CTRL {d.hex(' ')}", flush=True)


async def main():
    async with BleakClient(ADDR, timeout=30) as c:
        await c.start_notify(ML_N, on)
        await c.write_gatt_char(ML_W, bytes([0, 5]) + CLIENT + b"\0\0", response=True)
        await asyncio.sleep(1)
        for svc in range(2, 41):
            if svc == 1:
                continue
            await c.write_gatt_char(ML_W, bytes([0, 0]) + CLIENT + svc.to_bytes(2, "little") + b"\0", response=True)
            await asyncio.sleep(0.4)
        print("-- 25 s lauschen", flush=True)
        await asyncio.sleep(25)
        await c.write_gatt_char(ML_W, bytes([0, 5]) + CLIENT + b"\0\0", response=True)
        await asyncio.sleep(0.5)


asyncio.run(main())
