#!/usr/bin/env python3
"""BlueZ-Pairing mit Passkey aus Datei.

Startet Pair() auf dem Gerät, registriert einen Agenten. Fragt BlueZ nach dem
Passkey, wird ~/jarvis/garmin/passkey gepollt (bis 90 s). Code schreiben mit:
    echo 123456 > ~/jarvis/garmin/passkey
"""
import asyncio, sys, time
from pathlib import Path
from dbus_fast.aio import MessageBus
from dbus_fast import BusType, Variant
from dbus_fast.service import ServiceInterface, method

ADDR = sys.argv[1] if len(sys.argv) > 1 else __import__("devaddr").addr()
DEV = "/org/bluez/hci0/dev_" + ADDR.replace(":", "_")
AGENT = "/jarvis/garmin/agent"
KEYFILE = Path(__file__).resolve().parent / "passkey"


async def wait_key(timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if KEYFILE.exists():
            s = KEYFILE.read_text().strip()
            if s.isdigit():
                KEYFILE.unlink()
                return int(s)
        await asyncio.sleep(0.2)
    raise TimeoutError("kein Passkey erhalten")


class Agent(ServiceInterface):
    def __init__(self):
        super().__init__("org.bluez.Agent1")

    @method()
    async def RequestPasskey(self, device: "o") -> "u":
        print("PASSKEY ANGEFRAGT – Code von der Uhr in", KEYFILE, flush=True)
        k = await wait_key()
        print("Passkey gesendet", flush=True)
        return k

    @method()
    async def RequestPinCode(self, device: "o") -> "s":
        print("PIN ANGEFRAGT", flush=True)
        return str(await wait_key())

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):
        print("DisplayPasskey", passkey, flush=True)

    @method()
    def RequestConfirmation(self, device: "o", passkey: "u"):
        print("Bestätigung angefragt, Passkey", f"{passkey:06d}", "-> akzeptiert", flush=True)

    @method()
    def RequestAuthorization(self, device: "o"):
        print("Autorisierung -> ok", flush=True)

    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):
        pass

    @method()
    def Cancel(self):
        print("Abgebrochen von BlueZ", flush=True)

    @method()
    def Release(self):
        pass


async def main():
    KEYFILE.unlink(missing_ok=True)
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    bus.export(AGENT, Agent())
    intro = await bus.introspect("org.bluez", "/org/bluez")
    mgr = bus.get_proxy_object("org.bluez", "/org/bluez", intro).get_interface("org.bluez.AgentManager1")
    await mgr.call_register_agent(AGENT, "KeyboardDisplay")
    await mgr.call_request_default_agent(AGENT)

    intro = await bus.introspect("org.bluez", DEV)
    obj = bus.get_proxy_object("org.bluez", DEV, intro)
    dev = obj.get_interface("org.bluez.Device1")
    props = obj.get_interface("org.freedesktop.DBus.Properties")
    print("Pairing mit", ADDR, "…", flush=True)
    try:
        await dev.call_pair()
        await props.call_set("org.bluez.Device1", "Trusted", Variant("b", True))
        print("PAIRING ERFOLGREICH", flush=True)
    except Exception as e:
        print("PAIRING FEHLGESCHLAGEN:", e, flush=True)
        sys.exit(1)
    finally:
        try:
            await mgr.call_unregister_agent(AGENT)
        except Exception:
            pass


asyncio.run(main())
