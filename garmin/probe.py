#!/usr/bin/env python3
"""Rohprobe: Legacy- und Multi-Link-Kanal der fenix abhören, ML-Handshake versuchen."""
import asyncio, sys, time
from bleak import BleakClient

ADDR = sys.argv[1] if len(sys.argv) > 1 else __import__("devaddr").addr()
U = lambda s: f"6a4e{s}-667b-11e3-949a-0800200c9a66"
LEG_W, LEG_N = U("4c80"), U("cd28")
ML_W, ML_N = U("2820"), U("2810")
CLIENT = (2).to_bytes(8, "little")
t0 = time.time()


def log(tag, data):
    print(f"{time.time()-t0:6.2f} {tag:<10} {data.hex(' ')}", flush=True)


async def main():
    async with BleakClient(ADDR, timeout=30) as c:
        print("verbunden, MTU", c.mtu_size, flush=True)
        await c.start_notify(LEG_N, lambda _, d: log("LEGACY<", d))
        for n in ("2810", "2811", "2812", "2813", "2814"):
            await c.start_notify(U(n), lambda ch, d, n=n: log(f"ML{n}<", d))
        print("-- 4 s passiv lauschen", flush=True)
        await asyncio.sleep(4)

        print("-- ML CLOSE_ALL", flush=True)
        pkt = bytes([0x00, 0x05]) + CLIENT + b"\x00\x00"
        log("ML>", pkt); await c.write_gatt_char(ML_W, pkt, response=True)
        await asyncio.sleep(2)

        for svc, name in ((4, "REGISTRATION"), (1, "GFDI")):
            print(f"-- ML REGISTER {name}", flush=True)
            pkt = bytes([0x00, 0x00]) + CLIENT + svc.to_bytes(2, "little") + b"\x00"
            log("ML>", pkt); await c.write_gatt_char(ML_W, pkt, response=True)
            await asyncio.sleep(3)
        print("-- 8 s lauschen (GFDI DeviceInformation 5024 erwartet)", flush=True)
        await asyncio.sleep(8)


asyncio.run(main())
