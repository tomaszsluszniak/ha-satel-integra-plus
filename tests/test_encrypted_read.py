"""The library read a fragmented encrypted PDU only partially; the patch reads it whole."""

import asyncio
import importlib.util
from pathlib import Path
import sys

from satel_integra.transport import SatelEncryptedTransport

orig = SatelEncryptedTransport._read_from_transport


async def run(func):
    t = SatelEncryptedTransport("x", 1, "key")
    t._reader = asyncio.StreamReader()
    t._reader.feed_data(bytes([32]) + b"A" * 10)

    async def later():
        await asyncio.sleep(0.05)
        t._reader.feed_data(b"B" * 22)

    asyncio.get_running_loop().create_task(later())
    return await func(t)


partial = asyncio.run(run(orig))
spec = importlib.util.spec_from_file_location(
    "satel_ext",
    Path(__file__).parent.parent / "custom_components/satel_integra/satel_ext.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["satel_ext"] = m
spec.loader.exec_module(m)
full = asyncio.run(run(SatelEncryptedTransport._read_from_transport))
print("library:", len(partial), "patched:", len(full))
assert len(partial) == 10 and len(full) == 32
