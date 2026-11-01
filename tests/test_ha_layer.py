"""Exercise the HA layer (entities, services) with stubbed HA and the ETHM simulator."""

import asyncio
import importlib
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).parent))
import ha_stubs  # noqa: E402

ha_stubs.install()

from test_satel_ext import ExtSim, wait_until  # noqa: E402

# import the integration package under a different name (the library is "satel_integra")
spec = importlib.util.spec_from_file_location(
    "cc_satel",
    Path(__file__).parent.parent / "custom_components/satel_integra/__init__.py",
    submodule_search_locations=[
        str(Path(__file__).parent.parent / "custom_components/satel_integra")
    ],
)
cc = importlib.util.module_from_spec(spec)
sys.modules["cc_satel"] = cc
spec.loader.exec_module(cc)

acp = importlib.import_module("cc_satel.alarm_control_panel")
bs = importlib.import_module("cc_satel.binary_sensor")
sw = importlib.import_module("cc_satel.switch")
ev = importlib.import_module("cc_satel.event")
services = importlib.import_module("cc_satel.services")
coord = importlib.import_module("cc_satel.coordinator")
client_mod = importlib.import_module("cc_satel.client")
diag = importlib.import_module("cc_satel.diagnostics")
State = ha_stubs.AlarmControlPanelState


class Subentry:
    def __init__(self, subentry_type, data, sid):
        self.subentry_type, self.data, self.subentry_id = subentry_type, data, sid
        self.title = f"{data['name']}"


class Entry:
    def __init__(self, port, options):
        self.entry_id = "E1"
        self.data = {"host": "127.0.0.1", "port": port, "encryption_key": None}
        self.options = options
        self.subentries = {}
        self.state = ha_stubs.ConfigEntryState.LOADED
        subs = [
            Subentry(
                "partition",
                {"name": "Wiatrolap", "partition_number": 1, "arm_home_mode": 3},
                "p1",
            ),
            Subentry(
                "partition",
                {"name": "Garaz", "partition_number": 2, "arm_home_mode": 3},
                "p2",
            ),
            Subentry(
                "partition",
                {"name": "Piwnica", "partition_number": 3, "arm_home_mode": 2},
                "p3",
            ),
            Subentry(
                "partition",
                {"name": "Parter", "partition_number": 4, "arm_home_mode": 3},
                "p4",
            ),
            Subentry(
                "zone",
                {
                    "name": "Drzwi",
                    "zone_number": 7,
                    "type": "door",
                    "enable_temperature_sensor": False,
                },
                "z7",
            ),
            Subentry(
                "switchable_output",
                {"name": "Rolety", "switchable_output_number": 3},
                "o3",
            ),
        ]
        self.subentries = {s.subentry_id: s for s in subs}
        self.unloads = []

    def get_subentries_of_type(self, t):
        return [s for s in self.subentries.values() if s.subentry_type == t]

    def async_on_unload(self, f):
        self.unloads.append(f)


class Bus:
    def __init__(self):
        self.fired = []

    def async_fire(self, name, data):
        self.fired.append((name, data))


class Hass:
    def __init__(self):
        self.bus = Bus()
        self.services = types.SimpleNamespace(
            registered={},
            async_register=lambda d, s, h, schema=None, supports_response=None: (
                self.services.registered.__setitem__(s, h)
            ),
        )
        self.config_entries = types.SimpleNamespace(
            async_entries=lambda d: [self.entry]
        )


async def main():
    sim = ExtSim()
    sim.faults.mask_bytes = 16
    await sim.start()
    hass = Hass()
    entry = Entry(
        sim.port,
        {
            "code": "1234",
            "all_partitions_panel": True,
            "all_partitions": [],
            "event_log_interval": 10,
        },
    )
    hass.entry = entry
    client = client_mod.SatelClient(hass, entry)
    C = coord
    cz = C.SatelIntegraZonesCoordinator(hass, entry, client)
    co = C.SatelIntegraOutputsCoordinator(hass, entry, client)
    cp = C.SatelIntegraPartitionsCoordinator(hass, entry, client)
    cs = C.SatelIntegraSystemStatusCoordinator(hass, entry, client)
    cx = C.SatelIntegraExtCoordinator(hass, entry, client)
    ce = C.SatelIntegraEventLogCoordinator(hass, entry, client)
    for c in (cz, co, cp, cs, cx):
        c.setup()
    await client.async_connect()
    try:
        entry.runtime_data = C.SatelIntegraData(
            client, None, cz, co, cp, None, cs, cx, ce
        )
        assert (
            client.module_info is not None
            and client.module_info.supports_256_zones_outputs
        )

        added = []
        add = lambda ents, config_subentry_id=None: added.extend(ents)
        for platform in (acp, bs, sw, ev):
            await platform.async_setup_entry(hass, entry, add)
        names = sorted(type(e).__name__ for e in added)
        print(len(added), "entities:", {n: names.count(n) for n in set(names)})
        uids = [e.unique_id for e in added]
        assert len(uids) == len(set(uids)), "duplicate unique ids"
        assert (
            "E1_alarm_panel_1" in uids
            and "E1_zones_7" in uids
            and "E1_switch_3" in uids
        )  # core IDs kept
        all_panel = next(
            e for e in added if isinstance(e, acp.SatelIntegraAllPartitionsPanel)
        )
        p1 = next(
            e
            for e in added
            if isinstance(e, acp.SatelIntegraAlarmPanel) and e._device_number == 1
        )
        for e in added:
            e.hass = hass
            await e.async_added_to_hass()
        assert all_panel._attr_code_format == ha_stubs.CodeFormat.NUMBER

        # arm away all -> one frame for 4 partitions
        sim.received.clear()
        await all_panel.async_alarm_arm_away("1234")
        frames = [f for f in sim.received if f[0] == 0x80]
        assert len(frames) == 1 and frames[0][9] == 0x0F, frames
        assert await wait_until(
            lambda: cp.data.get(acp.AlarmState.ARMED_MODE0) == [1, 2, 3, 4]
        )
        assert (
            all_panel.alarm_state == State.ARMED_AWAY
            and p1.alarm_state == State.ARMED_AWAY
        )
        # disarm all -> one frame
        sim.received.clear()
        await all_panel.async_alarm_disarm("1234")
        assert [f[9] for f in sim.received if f[0] == 0x84] == [0x0F]
        assert await wait_until(lambda: all_panel.alarm_state == State.DISARMED)
        # all Satel modes on the panel buttons (default option)
        F = ha_stubs.AlarmControlPanelEntityFeature
        assert all_panel._attr_supported_features == F.ARM_AWAY | F.ARM_HOME | F.ARM_NIGHT | F.ARM_CUSTOM_BYPASS
        assert all_panel._attr_translation_key == "all_partitions_modes" and p1._attr_translation_key == "partition"
        for action, cmd in (
            (all_panel.async_alarm_arm_home, 0x82),
            (all_panel.async_alarm_arm_night, 0x83),
            (all_panel.async_alarm_arm_custom_bypass, 0x81),
        ):
            sim.received.clear()
            await action("1234")
            frames = [(f[0], f[9]) for f in sim.received if 0x80 <= f[0] <= 0x83]
            assert frames == [(cmd, 0x0F)], frames
        sim.received.clear()
        await p1.async_alarm_arm_night("1234")
        assert [(f[0], f[9]) for f in sim.received if 0x80 <= f[0] <= 0x83] == [(0x83, 1)]
        # partial arming
        await p1.async_alarm_disarm("1234")
        assert await wait_until(lambda: all_panel.extra_state_attributes["partially_armed"])
        attrs = all_panel.extra_state_attributes
        assert attrs["disarmed_partitions"] == ["Wiatrolap"], attrs
        assert all_panel.alarm_state == State.ARMED_AWAY

        # classic mode: arm home uses the per-partition modes, grouped per mode
        classic = acp.SatelIntegraAllPartitionsPanel(
            cp, cx, "E1",
            {n: s for n, s in ((s.data["partition_number"], s) for s in entry.get_subentries_of_type("partition"))},
            False, False,
        )
        assert classic._attr_supported_features == F.ARM_HOME | F.ARM_AWAY
        sim.received.clear()
        await classic.async_alarm_arm_home("1234")
        home = sorted((f[0], f[9]) for f in sim.received if 0x80 <= f[0] <= 0x83)
        assert home == [(0x82, 0b0100), (0x83, 0b1011)], home

        # state mapping per mode
        AS = acp.AlarmState
        data = {AS.ARMED_MODE0: [1, 2, 3, 4], AS.ARMED_MODE1: [1], AS.ARMED_MODE2: [2], AS.ARMED_MODE3: [3]}
        assert [acp.partition_alarm_state(data, n, True) for n in (1, 2, 3, 4)] == [
            State.ARMED_CUSTOM_BYPASS, State.ARMED_HOME, State.ARMED_NIGHT, State.ARMED_AWAY]
        assert [acp.partition_alarm_state(data, n) for n in (1, 2, 3, 4)] == [
            State.ARMED_HOME, State.ARMED_HOME, State.ARMED_HOME, State.ARMED_AWAY]
        assert [acp.partition_armed_mode(data, n) for n in (1, 2, 3, 4, 5)] == [1, 2, 3, 0, None]
        assert acp.combined_alarm_state([State.ARMED_NIGHT, State.DISARMED], True) == State.ARMED_NIGHT
        assert acp.combined_alarm_state([State.ARMED_NIGHT, State.ARMED_HOME], True) == State.ARMED_HOME
        assert acp.combined_alarm_state([State.ARMED_HOME, State.DISARMED]) == State.ARMED_CUSTOM_BYPASS
        print("all panel attrs:", attrs)

        # missing code (no stored code use) -> validation error
        try:
            await p1.async_alarm_arm_away(None)
        except ha_stubs.ServiceValidationError as err:
            assert err.translation_key == "missing_alarm_access_code"
        # rejection is translated
        sim.faults.reject_code = 0x01
        try:
            await p1.async_alarm_arm_away("9999")
        except ha_stubs.HomeAssistantError as err:
            assert err.translation_key == "command_rejected_wrong_code", (
                err.translation_key
            )
        else:
            raise AssertionError
        sim.faults.reject_code = None

        # zone flags and bypass switch
        tamper = next(
            e
            for e in added
            if isinstance(e, bs.SatelIntegraZoneFlagBinarySensor)
            and e.entity_description.key == "tamper"
        )
        bypass = next(
            e for e in added if isinstance(e, sw.SatelIntegraZoneBypassSwitch)
        )
        assert tamper.unique_id == "E1_zones_7_tamper" and tamper.is_on is False
        sim.set_tamper(7, True)
        assert await wait_until(lambda: tamper.is_on is True)
        await bypass.async_turn_on()
        assert await wait_until(lambda: bypass.is_on is True)
        await bypass.async_turn_off()
        assert await wait_until(lambda: bypass.is_on is False)
        viol = next(
            e
            for e in added
            if isinstance(e, bs.SatelIntegraPartitionFlagBinarySensor)
            and e.entity_description.key == "violated_zones"
            and e._device_number == 2
        )
        sim.violated_partitions.add(2)
        sim._after_change(0x25)
        assert await wait_until(lambda: viol.is_on is True)
        assert all_panel.extra_state_attributes["ready_to_arm"] is False

        # system status sensors exist and read None/False
        svc = next(
            e
            for e in added
            if getattr(e.entity_description, "key", "") == "service_mode"
        )
        assert svc.is_on in (False, None)

        # output switch with result
        out = next(e for e in added if isinstance(e, sw.SatelIntegraSwitch))
        await out.async_turn_on()
        assert await wait_until(lambda: co.data.get(3) is True)

        # services
        services.async_setup_services(hass)
        handler = hass.services.registered["arm"]
        call = lambda svc, **data: types.SimpleNamespace(
            hass=hass, service=svc, data=data
        )
        sim.received.clear()
        await handler(
            call(
                "arm",
                code="1234",
                partitions=[1, 2],
                mode=0,
                force=True,
                no_bypass=False,
            )
        )
        assert sim.received[-1][0] == 0xA0
        # the stored code controls the alarm only with the panel option enabled
        try:
            await handler(call("disarm", clear_alarm=True))
        except services.ServiceValidationError:
            pass
        else:
            raise AssertionError("disarm with the stored code not rejected")
        await handler(call("disarm", code="1234", clear_alarm=True))
        assert [f[0] for f in sim.received[-2:]] == [0x84, 0x85]
        await handler(call("bypass_zones", zones=[7], isolate=True))
        assert sim.last_control[0] == 0x90
        await handler(call("set_outputs", outputs=[3, 5], state="toggle"))
        res = await handler(call("read_event_log", count=5))
        assert len(res["events"]) == 2 and res["events"][0]["source_name"] == "Tomek", (
            res
        )
        print("event log:", res["events"][0])

        # event coordinator: first poll remembers position, then new events are fired
        ent = next(e for e in added if isinstance(e, ev.SatelIntegraEventLogEntity))
        await ce.async_refresh()
        assert ce.data == [] and not hass.bus.fired
        rec = bytes(
            [
                0x20 | 0x10 | (2 << 6),
                (2 << 5) | 1,
                (11 << 4) | 0x4,
                0x30,
                (2 << 3),
                0x0A,
                3,
                0,
            ]
        )
        sim.events.insert(0, (rec, 0x103))
        await ce.async_refresh()
        assert [d["index"] for _, d in hass.bus.fired] == [0x103], hass.bus.fired
        assert ent.triggered[-1][0] == "arming"
        n = len(ent.triggered)
        ce.async_update_listeners()  # e.g. connection change - must not re-trigger
        assert len(ent.triggered) == n
        print("ALL HA LAYER CHECKS OK")
    finally:
        for f in entry.unloads:
            f()
        await client.async_close()
        await sim.stop()


asyncio.run(main())
