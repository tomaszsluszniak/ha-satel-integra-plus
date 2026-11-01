"""Coordinator for Satel Integra."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.debounce import Debouncer
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
        self._debouncer = Debouncer(
            hass=self.hass,
            logger=_LOGGER,
            cooldown=PARTITION_UPDATE_DEBOUNCE_DELAY,
            immediate=False,
            function=callback(
                lambda: self.async_set_updated_data(
                    dict(self.client.controller.state.partition_states)
                )
            ),
        )

    @override
    def setup(self) -> None:
        """Set up client callbacks for this coordinator."""
        super().setup()
        self.config_entry.async_on_unload(self._debouncer.async_shutdown)
        self.config_entry.async_on_unload(
            self.client.controller.add_alarm_status_callback(
                self.partitions_update_callback
            )
        )

    @callback
    def partitions_update_callback(self) -> None:
        """Update partition objects as per notification from the alarm."""
        self._debouncer.async_schedule_call()


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
