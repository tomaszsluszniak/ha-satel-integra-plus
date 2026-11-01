"""Tests of satel_ext.SatelExtended against the ETHM-1 Plus simulator of the library.

Run: PYTHONPATH=<satel_integra repo>:<satel_integra repo>/tools/ethm_simulator python -m tests.test_satel_ext
(no pytest-asyncio needed).
"""

import asyncio
from datetime import datetime
import importlib.util
import logging
from pathlib import Path
import sys

import ethm_simulator as sim_mod
from ethm_simulator import EthmSimulator, from_mask, mask
from satel_integra import SatelCommandRejectedError, SatelResultCode

_spec = importlib.util.spec_from_file_location(
    "satel_ext",
    Path(__file__).parent.parent / "custom_components/satel_integra/satel_ext.py",
)
satel_ext = importlib.util.module_from_spec(_spec)
sys.modules["satel_ext"] = satel_ext
_spec.loader.exec_module(satel_ext)

SatelExtended = satel_ext.SatelExtended
X = satel_ext.SatelExtReadCommand

logging.basicConfig(level=logging.WARNING)


class ExtSim(EthmSimulator):
    """Simulator that also knows the extended commands."""

    def __init__(self) -> None:
        super().__init__()
        self.tamper: set[int] = set()
        self.bypassed: set[int] = set()
        self.violated_partitions: set[int] = set()
        self.last_control: tuple[int, bytes] | None = None
        self.events = [
            # newest first: (record, index)
            (
                bytes(
                    [
                        0x20 | 0x10 | (2 << 6),
                        (2 << 5) | 1,
                        (11 << 4) | 0x4,
                        0x2B,
                        (1 << 3),
                        0x0A,
                        3,
                        0,
                    ]
                ),
                0x000102,
            ),
            (
                bytes(
                    [
                        0x20 | 0x10 | (2 << 6),
                        (0 << 5) | 1,
                        (11 << 4) | 0x4,
                        0x10,
                        (1 << 3),
                        0x01,
                        7,
                        0,
                    ]
                ),
                0x000101,
            ),
            (bytes(8), 0x000100),  # end of events
        ]
        sim_mod._READS[0x01] = lambda s: mask(self.tamper, 16)
        sim_mod._READS[0x06] = lambda s: mask(self.bypassed, 16)
        sim_mod._READS[0x25] = lambda s: mask(self.violated_partitions, 4)

    def set_tamper(self, zone: int, on: bool) -> None:
        (self.tamper.add if on else self.tamper.discard)(zone)
        self._after_change(0x01)

    async def _command(self, payload: bytes) -> None:
        cmd, data = payload[0], payload[1:]
        if (
            cmd in (0x86, 0x87, 0x90, 0x91, 0x8B)
            or 0xA0 <= cmd <= 0xA3
            or (0x80 <= cmd <= 0x83 and len(data) == 13)
        ):
            self.last_control = (cmd, bytes(data))
            if self.faults.reject_code is not None:
                self._send(0xEF, bytes([self.faults.reject_code]))
                return
            self._send(0xEF, b"\x00" if cmd >= 0xA0 or cmd <= 0x83 else b"\xff")
            if cmd in (0x86, 0x90):
                self.bypassed |= from_mask(data[8:])
                self._after_change(0x06)
            elif cmd == 0x91:
                for n in from_mask(data[8:]):
                    self.output(n, n not in self.state.outputs)
            elif cmd == 0x87:
                self.bypassed -= from_mask(data[8:])
                self._after_change(0x06)
            elif cmd >= 0xA0:
                for n in from_mask(data[8:12]):
                    self.arming(n, True)
            return
        if cmd == 0x8C:
            idx = bytes(data)
            if idx == b"\xff\xff\xff":
                rec, index = self.events[0]
            else:
                pos = next(
                    i
                    for i, (_, ix) in enumerate(self.events)
                    if ix == int.from_bytes(idx, "big")
                )
                rec, index = self.events[pos + 1]
            self._send(0x8C, rec + index.to_bytes(3, "big") + idx)
            return
        if cmd == 0x8F:
            text = {0x0A: "Wylaczenie czuwania", 0x01: "Alarm z wejscia"}.get(
                data[1], "?"
            )
            self._send(
                0x8F,
                bytes(data[:2])
                + bytes([2 if data[1] == 0x0A else 1, 0, 0])
                + text.encode().ljust(46),
            )
            return
        if cmd == 0xEE:
            names = {(0, 1): "Wiatrolap", (1, 7): "Drzwi wejsciowe", (2, 3): "Tomek"}
            name = names.get((data[0], data[1]), "?")
            self._send(
                0xEE, bytes([data[0], data[1], 0]) + name.encode().ljust(16) + b"\x00"
            )
            return
        await super()._command(payload)


async def wait_until(predicate, timeout=3.0):
    for _ in range(int(timeout / 0.02)):
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return predicate()


async def main() -> None:
    sim = ExtSim()
    sim.faults.mask_bytes = 16
    await sim.start()
    sat = SatelExtended("127.0.0.1", sim.port, [1, 2], [3], [1, 2])
    assert await sat.connect()
    await sat.start(enable_monitoring=True)
    try:
        # monitoring includes extended commands and they are decoded
        assert await wait_until(lambda: X.ZONES_TAMPER in sat.ext_state.zones), (
            "no tamper data"
        )
        assert 0x01 in sim._autonomous and 0x25 in sim._autonomous
        notified = []
        sat.add_ext_state_callback(lambda: notified.append(1))
        sim.set_tamper(5, True)
        assert await wait_until(lambda: sat.ext_state.zone_flag(X.ZONES_TAMPER, 5)), (
            "tamper not seen"
        )
        assert notified
        # library state still works
        sim.zone_violation(2, True)
        assert await wait_until(lambda: sat.state.zones[2].violated is True)

        # bypass / unbypass with 16-byte mask
        r = await sat.bypass_zones("1234", [3, 7])
        assert r.is_success
        cmd, data = sim.last_control
        assert (
            cmd == 0x86
            and len(data) == 8 + 16
            and data[:8] == bytes.fromhex("1234FFFFFFFFFFFF")
        )
        assert await wait_until(lambda: sat.ext_state.zone_flag(X.ZONES_BYPASS, 7))
        await sat.bypass_zones("1234", [7], bypass=False)
        assert await wait_until(
            lambda: sat.ext_state.zone_flag(X.ZONES_BYPASS, 7) is False
        )

        # force arm and no-bypass arm
        r = await sat.arm_ext("1234", [1, 2], 3, force=True)
        assert r.code == SatelResultCode.OK
        assert sim.last_control[0] == 0xA3 and sim.last_control[1][8:12] == bytes(
            [3, 0, 0, 0]
        )
        await sat.arm_ext("1234", [1], 0, no_bypass=True)
        assert sim.last_control[0] == 0x80 and sim.last_control[1][12] == 0x80

        # rejected command is reported
        sim.faults.reject_code = 0x11
        try:
            await sat.arm_ext("1234", [1], 0, force=True)
        except SatelCommandRejectedError as err:
            assert err.result.code == SatelResultCode.CANNOT_ARM_CAN_FORCE
        else:
            raise AssertionError("rejection not raised")
        sim.faults.reject_code = None

        # plain arm via the library, grouped arming of several partitions
        await asyncio.gather(sat.arm("1234", [3], 0), sat.arm("1234", [4], 0))
        assert await wait_until(lambda: {3, 4} <= sim.state.armed)

        # event log
        assert await sat.read_last_event_index() == 0x000102
        events = await sat.read_events(10, with_texts=True)
        assert [e.index for e in events] == [0x102, 0x101], events
        e0, e1 = events
        assert (
            e0.event_class == "arming"
            and e0.text.startswith("Wylaczenie")
            and e0.source_name == "Tomek"
        )
        assert e0.partition == 1 and e0.partition_name == "Wiatrolap"
        assert e1.event_class == "zone_alarm" and e1.source_name == "Drzwi wejsciowe"
        assert (
            e0.timestamp.month == 11
            and e0.timestamp.day == 1
            and e0.timestamp.hour == 17
            and e0.timestamp.minute == 47
        )
        assert e0.timestamp.year % 4 == 2
        newer = await sat.read_events(10, stop_at_index=0x101, with_texts=False)
        assert [e.index for e in newer] == [0x102]

        # keepalive/RTC queries still fine after ext traffic
        assert sat.connected and sat.monitoring_ready
        print("ALL OK")
    finally:
        await sat.close()
        await sim.stop()


def test_decode_year() -> None:
    now = datetime(2026, 11, 1, 18, 0)
    rec = bytes([0x30 | (2 << 6), (2 << 5) | 1, (11 << 4), 0, 0, 0, 0, 0])
    assert satel_ext.decode_event_record(rec, 1, now).timestamp.year == 2026
    rec = bytes([0x30 | (1 << 6), (2 << 5) | 31, (12 << 4), 0, 0, 0, 0, 0])
    assert satel_ext.decode_event_record(rec, 1, now).timestamp.year == 2025
    assert satel_ext.decode_event_record(bytes(8), 1, now) is None


if __name__ == "__main__":
    test_decode_year()
    asyncio.run(main())
