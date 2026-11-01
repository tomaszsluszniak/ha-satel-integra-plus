"""Support for Satel Integra modifiable outputs represented as switches."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_CODE, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_SWITCHABLE_OUTPUT_NUMBER,
    CONF_ZONE_NUMBER,
    DOMAIN,
    SUBENTRY_TYPE_SWITCHABLE_OUTPUT,
    SUBENTRY_TYPE_ZONE,
)
from .coordinator import (
    SatelConfigEntry,
    SatelIntegraExtCoordinator,
    SatelIntegraOutputsCoordinator,
)
from .entity import SatelIntegraEntity
from .helpers import async_validate_command
from .satel_ext import SatelExtReadCommand

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SatelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Satel Integra switch devices."""

    runtime_data = config_entry.runtime_data

    for subentry in config_entry.get_subentries_of_type(
        SUBENTRY_TYPE_SWITCHABLE_OUTPUT
    ):
        switchable_output_num: int = subentry.data[CONF_SWITCHABLE_OUTPUT_NUMBER]

        async_add_entities(
            [
                SatelIntegraSwitch(
                    runtime_data.coordinator_outputs,
                    config_entry.entry_id,
                    subentry,
                    switchable_output_num,
                    config_entry.options.get(CONF_CODE),
                ),
            ],
            config_subentry_id=subentry.subentry_id,
        )

    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_ZONE):
        async_add_entities(
            [
                SatelIntegraZoneBypassSwitch(
                    runtime_data.coordinator_ext,
                    config_entry.entry_id,
                    subentry,
                    subentry.data[CONF_ZONE_NUMBER],
                    config_entry.options.get(CONF_CODE),
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SatelIntegraSwitch(
    SatelIntegraEntity[SatelIntegraOutputsCoordinator], SwitchEntity
):
    """Representation of an Satel Integra switch."""

    _attr_name = None

    def __init__(
        self,
        coordinator: SatelIntegraOutputsCoordinator,
        config_entry_id: str,
        subentry: ConfigSubentry,
        device_number: int,
        code: str | None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator,
            config_entry_id,
            subentry,
            device_number,
        )

        self._code = code

        self._attr_is_on = self._get_state_from_coordinator()

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self._get_state_from_coordinator()
        self.async_write_ha_state()

    def _get_state_from_coordinator(self) -> bool | None:
        """Method to get switch state from coordinator data."""
        return self.coordinator.data.get(self._device_number)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if self._code is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="missing_output_access_code",
            )

        await async_validate_command(
            self._controller.set_output(
                self._code, self._device_number, True, wait_for_result=True
            )
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        if self._code is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="missing_output_access_code",
            )

        await async_validate_command(
            self._controller.set_output(
                self._code, self._device_number, False, wait_for_result=True
            )
        )
        self._attr_is_on = False
        self.async_write_ha_state()


class SatelIntegraZoneBypassSwitch(
    SatelIntegraEntity[SatelIntegraExtCoordinator], SwitchEntity
):
    """Zone bypass (blokada wejścia): on = bypassed."""

    _attr_translation_key = "zone_bypass"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: SatelIntegraExtCoordinator,
        config_entry_id: str,
        subentry: ConfigSubentry,
        device_number: int,
        code: str | None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator, config_entry_id, subentry, device_number, "bypass"
        )
        self._code = code

    @property
    @override
    def is_on(self) -> bool | None:
        """Return True if the zone is bypassed or isolated."""
        data = self.coordinator.data
        bypassed = data.zone_flag(SatelExtReadCommand.ZONES_BYPASS, self._device_number)
        isolated = data.zone_flag(
            SatelExtReadCommand.ZONES_ISOLATE, self._device_number
        )
        if bypassed is None:
            return None
        return bypassed or bool(isolated)

    async def _bypass(self, bypass: bool) -> None:
        if self._code is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="missing_output_access_code",
            )
        await async_validate_command(
            self._controller.bypass_zones(
                self._code, [self._device_number], bypass=bypass
            )
        )

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Bypass the zone."""
        await self._bypass(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unbypass the zone."""
        await self._bypass(False)
