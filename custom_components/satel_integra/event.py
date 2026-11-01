"""Panel event log exposed as an event entity."""

from typing import override

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SatelConfigEntry, SatelIntegraEventLogCoordinator
from .entity import SatelIntegraBaseEntity
from .satel_ext import EVENT_CLASSES

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SatelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event log entity."""
    coordinator = config_entry.runtime_data.coordinator_events
    if coordinator is not None:
        async_add_entities(
            [SatelIntegraEventLogEntity(coordinator, config_entry.entry_id)]
        )


class SatelIntegraEventLogEntity(
    SatelIntegraBaseEntity[SatelIntegraEventLogCoordinator], EventEntity
):
    """Newest record of the panel event log."""

    _attr_translation_key = "event_log"
    _attr_event_types = list(EVENT_CLASSES.values())

    def __init__(
        self, coordinator: SatelIntegraEventLogCoordinator, config_entry_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_event_log"
        self._processed: list | None = coordinator.data

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Trigger an entity event for every new log record."""
        events = self.coordinator.data or []
        if events is self._processed:
            # listeners are also notified on connection changes - no new data
            self.async_write_ha_state()
            return
        self._processed = events
        for event in events:
            data = event.as_dict()
            event_type = data.pop("class")
            self._trigger_event(event_type, data)
            # one state write per event, so every record is a distinct change
            self.async_write_ha_state()
        if not events:
            self.async_write_ha_state()

    @property
    @override
    def available(self) -> bool:
        """Stay available between polls even if one poll failed."""
        return self._controller.connected
