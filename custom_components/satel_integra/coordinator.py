"""Coordinator for Satel Integra."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import time
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from satel_integra import (
    AlarmState,
    SatelPanelInfo,
    SatelRtcAndStatus,
    SatelSystemTroubles,
)

from .client import SatelClient
from .const import (
    CONF_ENABLE_TEMPERATURE_SENSOR,
    CONF_EVENT_LOG_INTERVAL,
    CONF_ZONE_NUMBER,
    DEFAULT_EVENT_LOG_INTERVAL,
    EVENT_SATEL,
    SUBENTRY_TYPE_ZONE,
)
from .satel_ext import SatelEvent, SatelExtReadCommand

_LOGGER = logging.getLogger(__name__)

PARTITION_UPDATE_DEBOUNCE_DELAY = 0.15
# The module reports a newly armed partition in the "armed" list (0x0A, mode 0)
# about 3 s before it reports it in the list of its real mode (0x2A/0x0B/0x0C).
# Such a partition is shown as still arming until its mode is known: the mode
# lists are read at once, and without a mode 1-3 it is mode 0 after this time.
ARM_MODE_SETTLE_TIME = 6.0
# How long an arming in mode 0 sent from HA is expected (longest exit delay)
EXPECTED_MODE0_TIMEOUT = 300.0

_HIGHER_ARMED_MODES = (
    AlarmState.ARMED_MODE1,
    AlarmState.ARMED_MODE2,
    AlarmState.ARMED_MODE3,
)
TEMPERATURE_SENSOR_UPDATE_INTERVAL = timedelta(minutes=5)
EVENT_LOG_MAX_NEW_EVENTS = 30


@dataclass
class SatelIntegraData:
    """Data for the satel_integra integration."""

    client: SatelClient
    panel_info: SatelPanelInfo | None
    coordinator_zones: SatelIntegraZonesCoordinator
    coordinator_outputs: SatelIntegraOutputsCoordinator
    coordinator_partitions: SatelIntegraPartitionsCoordinator
    coordinator_temperatures: SatelIntegraTemperaturesCoordinator
    coordinator_system_status: SatelIntegraSystemStatusCoordinator
    coordinator_ext: SatelIntegraExtCoordinator
    coordinator_events: SatelIntegraEventLogCoordinator | None = None


type SatelConfigEntry = ConfigEntry[SatelIntegraData]


class SatelIntegraBaseCoordinator[_DataT](DataUpdateCoordinator[_DataT]):
    """DataUpdateCoordinator base class for Satel Integra."""

    config_entry: SatelConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SatelConfigEntry,
        client: SatelClient,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize the base coordinator."""
        self.client = client

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{entry.entry_id} {self.__class__.__name__}",
            update_interval=update_interval,
        )

    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        self.config_entry.async_on_unload(
            self.client.controller.add_connection_status_callback(
                self._async_handle_connection_state_update
            )
        )

    @callback
    def _async_handle_connection_state_update(self) -> None:
        """Notify listeners on connection state changes from the client."""
        self.async_update_listeners()


class SatelIntegraZonesCoordinator(SatelIntegraBaseCoordinator[dict[int, bool | None]]):
    """DataUpdateCoordinator to handle zone updates."""

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, entry, client)
        self.data = {}

    @override
    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        super().setup()
        self.config_entry.async_on_unload(
            self.client.controller.add_zone_changed_callback(self.zones_update_callback)
        )

    @callback
    def zones_update_callback(self) -> None:
        """Update zone objects as per notification from the alarm."""
        self.async_set_updated_data(
            {
                zone: zone_state.violated
                for zone, zone_state in self.client.controller.state.zones.items()
            }
        )


class SatelIntegraOutputsCoordinator(
    SatelIntegraBaseCoordinator[dict[int, bool | None]]
):
    """DataUpdateCoordinator to handle output updates."""

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, entry, client)
        self.data = {}

    @override
    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        super().setup()
        self.config_entry.async_on_unload(
            self.client.controller.add_output_changed_callback(
                self.outputs_update_callback
            )
        )

    @callback
    def outputs_update_callback(self) -> None:
        """Update output objects as per notification from the alarm."""
        self.async_set_updated_data(
            {
                output: output_state.active
                for output, output_state in self.client.controller.state.outputs.items()
            }
        )


def settle_arm_modes(
    data: dict[AlarmState, list[int]],
    previous: dict[AlarmState, list[int]],
    pending: dict[int, float],
    expected_mode0: dict[int, float],
    now: float,
) -> dict[AlarmState, list[int]]:
    """Hold back newly armed partitions whose arming mode is not reported yet.

    A partition that has just appeared in the mode 0 list without being in a
    mode 1-3 list is moved to the exit countdown list (shown as arming) until
    its mode list arrives, at most ARM_MODE_SETTLE_TIME after it was first seen
    (then it really is mode 0). `pending` (partition -> deadline) and
    `expected_mode0` (partitions armed in mode 0 from HA) are updated in place.
    """
    mode0 = data.get(AlarmState.ARMED_MODE0, [])
    for partition in [p for p in pending if p not in mode0]:
        del pending[partition]
    if AlarmState.ARMED_MODE0 not in previous:
        # First report after start: the partitions were armed before
        return data
    higher = {p for state in _HIGHER_ARMED_MODES for p in data.get(state, ())}
    shown = set(previous[AlarmState.ARMED_MODE0])
    held: list[int] = []
    for partition in mode0:
        if partition in higher or partition in shown:
            pending.pop(partition, None)
        elif expected_mode0.pop(partition, None) is not None:
            pending.pop(partition, None)
        elif now < pending.setdefault(partition, now + ARM_MODE_SETTLE_TIME):
            held.append(partition)
        else:
            del pending[partition]
    if not held:
        return data
    _LOGGER.debug("Arming mode of partitions %s not reported yet", held)
    settled = dict(data)
    settled[AlarmState.ARMED_MODE0] = [p for p in mode0 if p not in held]
    countdown = AlarmState.EXIT_COUNTDOWN_UNDER_10
    settled[countdown] = sorted({*data.get(countdown, ()), *held})
    return settled


class SatelIntegraPartitionsCoordinator(
    SatelIntegraBaseCoordinator[dict[AlarmState, list[int]]]
):
    """DataUpdateCoordinator to handle partition state updates."""

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, entry, client)
        self.data = {}
        self._pending: dict[int, float] = {}
        self._expected_mode0: dict[int, float] = {}
        self._cancel_recheck: Callable[[], None] | None = None
        self._debouncer = Debouncer(
            hass=self.hass,
            logger=_LOGGER,
            cooldown=PARTITION_UPDATE_DEBOUNCE_DELAY,
            immediate=False,
            function=self._publish,
        )

    @override
    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        super().setup()
        self.config_entry.async_on_unload(self._debouncer.async_shutdown)
        self.config_entry.async_on_unload(self._cancel_recheck_timer)
        self.config_entry.async_on_unload(
            self.client.controller.add_alarm_status_callback(
                self.partitions_update_callback
            )
        )

    @callback
    def partitions_update_callback(self) -> None:
        """Update partition objects as per notification from the alarm."""
        self._debouncer.async_schedule_call()

    def expect_arm_mode(self, partitions: Iterable[int], mode: int) -> None:
        """Note the mode of an arming sent from HA (mode 0 is shown at once)."""
        deadline = time.monotonic() + EXPECTED_MODE0_TIMEOUT
        for partition in partitions:
            if mode == 0:
                self._expected_mode0[partition] = deadline
            else:
                self._expected_mode0.pop(partition, None)

    @callback
    def _publish(self) -> None:
        now = time.monotonic()
        for partition, deadline in list(self._expected_mode0.items()):
            if deadline <= now:
                del self._expected_mode0[partition]
        waiting = set(self._pending)
        data = settle_arm_modes(
            dict(self.client.controller.state.partition_states),
            self.data,
            self._pending,
            self._expected_mode0,
            now,
        )
        if self._pending.keys() - waiting:
            # Ask for the mode lists instead of waiting for the module to report
            self.config_entry.async_create_background_task(
                self.hass,
                self.client.controller.refresh_arm_modes(),
                f"satel_integra {self.config_entry.entry_id} arm modes",
            )
        self._cancel_recheck_timer()
        if self._pending:
            self._cancel_recheck = async_call_later(
                self.hass, max(min(self._pending.values()) - now, 0), self._recheck
            )
        self.async_set_updated_data(data)

    @callback
    def _recheck(self, _now: datetime) -> None:
        self._cancel_recheck = None
        self._publish()

    @callback
    def _cancel_recheck_timer(self) -> None:
        if self._cancel_recheck is not None:
            self._cancel_recheck()
            self._cancel_recheck = None


@dataclass(frozen=True)
class SatelIntegraSystemStatusData:
    """System status and trouble data reported by the panel."""

    status: SatelRtcAndStatus | None
    troubles: SatelSystemTroubles | None


class SatelIntegraSystemStatusCoordinator(
    SatelIntegraBaseCoordinator[SatelIntegraSystemStatusData]
):
    """DataUpdateCoordinator to handle system status updates."""

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, entry, client)
        self.data = self._get_data()

    @override
    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        super().setup()
        self.config_entry.async_on_unload(
            self.client.controller.add_system_status_callback(
                self.system_status_update_callback
            )
        )

    @callback
    def system_status_update_callback(self) -> None:
        """Update the system status as per notification from the alarm."""
        data = self._get_data()
        if data != self.data:
            self.async_set_updated_data(data)

    def _get_data(self) -> SatelIntegraSystemStatusData:
        state = self.client.controller.state
        return SatelIntegraSystemStatusData(
            status=state.system_status, troubles=state.system_troubles
        )


@dataclass(frozen=True)
class SatelIntegraExtData:
    """Snapshot of the additionally monitored zone/partition flags."""

    zones: dict[SatelExtReadCommand, frozenset[int]] = field(default_factory=dict)
    partitions: dict[SatelExtReadCommand, frozenset[int]] = field(default_factory=dict)

    def zone_flag(self, command: SatelExtReadCommand, zone: int) -> bool | None:
        """Return the zone flag, None when not reported yet."""
        if command not in self.zones:
            return None
        return zone in self.zones[command]

    def partition_flag(
        self, command: SatelExtReadCommand, partition: int
    ) -> bool | None:
        """Return the partition flag, None when not reported yet."""
        if command not in self.partitions:
            return None
        return partition in self.partitions[command]


class SatelIntegraExtCoordinator(SatelIntegraBaseCoordinator[SatelIntegraExtData]):
    """Coordinator for zone tamper/bypass/... and extra partition flags."""

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, entry, client)
        self.data = SatelIntegraExtData()

    @override
    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        super().setup()
        self.config_entry.async_on_unload(
            self.client.controller.add_ext_state_callback(self.ext_update_callback)
        )

    @callback
    def ext_update_callback(self) -> None:
        """Take a snapshot of the extended state."""
        state = self.client.controller.ext_state
        self.async_set_updated_data(
            SatelIntegraExtData(
                zones={cmd: frozenset(v) for cmd, v in state.zones.items()},
                partitions={cmd: frozenset(v) for cmd, v in state.partitions.items()},
            )
        )


class SatelIntegraTemperaturesCoordinator(
    SatelIntegraBaseCoordinator[dict[int, float | None]]
):
    """DataUpdateCoordinator to poll zone temperatures."""

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            entry,
            client,
            update_interval=TEMPERATURE_SENSOR_UPDATE_INTERVAL,
        )

        self._zone_numbers = [
            subentry.data[CONF_ZONE_NUMBER]
            for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_ZONE)
            if subentry.data.get(CONF_ENABLE_TEMPERATURE_SENSOR, False)
        ]

    @override
    async def _async_update_data(self) -> dict[int, float | None]:
        """Fetch temperatures from the alarm."""
        if not self._zone_numbers:
            return {}

        try:
            return await self.client.controller.read_temperatures(self._zone_numbers)
        except Exception as err:
            raise UpdateFailed(f"Failed to fetch temperatures: {err}") from err


class SatelIntegraEventLogCoordinator(SatelIntegraBaseCoordinator[list[SatelEvent]]):
    """Polls the panel event log and fires an event for every new record.

    The protocol has no push for the event log, so the index of the newest
    record is polled (one short frame). New records are read with texts and
    names and fired as `satel_integra_event` on the event bus and on the event
    entity. The first poll only remembers the position (no history replay).
    """

    def __init__(
        self, hass: HomeAssistant, entry: SatelConfigEntry, client: SatelClient
    ) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(
            CONF_EVENT_LOG_INTERVAL, DEFAULT_EVENT_LOG_INTERVAL
        )
        super().__init__(
            hass, entry, client, update_interval=timedelta(seconds=interval)
        )
        self._last_index: int | None = None
        self._initialized = False
        self.data = []

    @override
    async def _async_update_data(self) -> list[SatelEvent]:
        controller = self.client.controller
        if not controller.connected:
            raise UpdateFailed("Not connected to the panel")
        try:
            newest = await controller.read_last_event_index()
            if not self._initialized:
                self._initialized = True
                self._last_index = newest
                return []
            if newest is None or newest == self._last_index:
                return []
            events = await controller.read_events(
                EVENT_LOG_MAX_NEW_EVENTS, stop_at_index=self._last_index
            )
        except Exception as err:
            raise UpdateFailed(f"Failed to read the event log: {err}") from err

        self._last_index = newest
        events.reverse()  # chronological order
        for event in events:
            self.hass.bus.async_fire(
                EVENT_SATEL,
                {"config_entry_id": self.config_entry.entry_id, **event.as_dict()},
            )
        return events
