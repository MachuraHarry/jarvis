#!/usr/bin/env python3
"""garmin-proto mit erzwungenem Multi-Link (fenix 5 Plus antwortet nicht auf Legacy-GFDI)."""
import sys
import garmin_proto_lab.transport as t
def _no_direct(services):
    raise t.TransportError("legacy GFDI disabled -> MultiLink")
t.select_gfdi_link = _no_direct
from garmin_proto_lab.cli import main
sys.exit(main())
