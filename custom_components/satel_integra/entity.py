"""Satel Integra base entity."""

from typing import TYPE_CHECKING, override

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_NAME
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SUBENTRY_TYPE_OUTPUT,
    SUBENTRY_TYPE_PARTITION,
    SUBENTRY_TYPE_SWITCHABLE_OUTPUT,
    SUBENTRY_TYPE_ZONE,
)
from .coordinator import SatelIntegraBaseCoordinator
from .satel_ext import SatelExtended

SubentryTypeToEntityType: dict[str, str] = {
    SUBENTRY_TYPE_PARTITION: "alarm_panel",
    SUBENTRY_TYPE_SWITCHABLE_OUTPUT: "switch",
    SUBENTRY_TYPE_ZONE: "zones",
    SUBENTRY_TYPE_OUTPUT: "outputs",
}


class SatelIntegraBaseEntity[_CoordinatorT: SatelIntegraBaseCoordinator](
    CoordinatorEntity[_CoordinatorT]
):
    """Satel Integra entity attached to the main panel device."""

    _attr_has_entity_name = True

    _controller: SatelExtended

    def __init__(self, coordinator: _CoordinatorT, config_entry_id: str) -> None:
        """Initialize the Satel Integra base entity."""
        super().__init__(coordinator)
        self._controller = coordinator.client.controller
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, config_entry_id)})

    @property
    @override
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._controller.connected


class SatelIntegraEntity[_CoordinatorT: SatelIntegraBaseCoordinator](
    SatelIntegraBaseEntity[_CoordinatorT]
):
    """Satel Integra entity attached to a partition/zone/output device.

    `key` adds further entities to the same device (e.g. zone tamper); the
    main entity keeps the unique ID used by the core integration.
    """

    def __init__(
        self,
        coordinator: _CoordinatorT,
        config_entry_id: str,
        subentry: ConfigSubentry,
        device_number: int,
        key: str | None = None,
    ) -> None:
        """Initialize the Satel Integra entity."""
        super().__init__(coordinator, config_entry_id)

        self._device_number = device_number

        entity_type = SubentryTypeToEntityType[subentry.subentry_type]

        if TYPE_CHECKING:
            assert entity_type is not None

        device_unique_id = f"{config_entry_id}_{entity_type}_{device_number}"
        self._attr_unique_id = f"{device_unique_id}_{key}" if key else device_unique_id

        self._attr_device_info = DeviceInfo(
            name=subentry.data[CONF_NAME],
            identifiers={(DOMAIN, device_unique_id)},
            via_device_id=dr.async_get_device_id_by_identifier(
                coordinator.hass,
                (DOMAIN, config_entry_id),
                config_entry_id=config_entry_id,
            ),
        )
