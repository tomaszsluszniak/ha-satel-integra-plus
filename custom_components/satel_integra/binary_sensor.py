"""Support for Satel Integra zone states- represented as binary sensors."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from satel_integra import SatelSystemTroubles, SatelTrouble, SatelTroubleType

from .const import (
    CONF_OUTPUT_NUMBER,
    CONF_PARTITION_NUMBER,
    CONF_ZONE_NUMBER,
    CONF_ZONE_TYPE,
    SUBENTRY_TYPE_OUTPUT,
    SUBENTRY_TYPE_PARTITION,
    SUBENTRY_TYPE_ZONE,
)
from .coordinator import (
    SatelConfigEntry,
    SatelIntegraBaseCoordinator,
    SatelIntegraExtCoordinator,
    SatelIntegraSystemStatusCoordinator,
    SatelIntegraSystemStatusData,
)
from .entity import SatelIntegraBaseEntity, SatelIntegraEntity
from .satel_ext import SatelExtReadCommand

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SatelExtFlagDescription(BinarySensorEntityDescription):
    """Describes a zone/partition flag from the extended monitoring."""

    command: SatelExtReadCommand


ZONE_FLAG_SENSORS = (
    SatelExtFlagDescription(
        key="tamper",
        translation_key="zone_tamper",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_category=EntityCategory.DIAGNOSTIC,
        command=SatelExtReadCommand.ZONES_TAMPER,
    ),
    SatelExtFlagDescription(
        key="alarm",
        translation_key="zone_alarm",
        device_class=BinarySensorDeviceClass.SAFETY,
        command=SatelExtReadCommand.ZONES_ALARM,
    ),
    SatelExtFlagDescription(
        key="alarm_memory",
        translation_key="zone_alarm_memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.ZONES_ALARM_MEMORY,
    ),
    SatelExtFlagDescription(
        key="tamper_alarm",
        translation_key="zone_tamper_alarm",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.ZONES_TAMPER_ALARM,
    ),
    SatelExtFlagDescription(
        key="isolated",
        translation_key="zone_isolated",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.ZONES_ISOLATE,
    ),
    SatelExtFlagDescription(
        key="masked",
        translation_key="zone_masked",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.ZONES_MASKED,
    ),
    SatelExtFlagDescription(
        key="no_violation_trouble",
        translation_key="zone_no_violation_trouble",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.ZONES_NO_VIOLATION_TROUBLE,
    ),
    SatelExtFlagDescription(
        key="long_violation_trouble",
        translation_key="zone_long_violation_trouble",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.ZONES_LONG_VIOLATION_TROUBLE,
    ),
)

PARTITION_FLAG_SENSORS = (
    SatelExtFlagDescription(
        key="violated_zones",
        translation_key="partition_violated_zones",
        device_class=BinarySensorDeviceClass.PROBLEM,
        command=SatelExtReadCommand.PARTITIONS_VIOLATED_ZONES,
    ),
    SatelExtFlagDescription(
        key="alarm_memory",
        translation_key="partition_alarm_memory",
        command=SatelExtReadCommand.PARTITIONS_ALARM_MEMORY,
    ),
    SatelExtFlagDescription(
        key="fire_alarm_memory",
        translation_key="partition_fire_alarm_memory",
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.PARTITIONS_FIRE_ALARM_MEMORY,
    ),
    SatelExtFlagDescription(
        key="temporary_blocked",
        translation_key="partition_temporary_blocked",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.PARTITIONS_TEMPORARY_BLOCKED,
    ),
    SatelExtFlagDescription(
        key="first_code_entered",
        translation_key="partition_first_code_entered",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.PARTITIONS_FIRST_CODE_ENTERED,
    ),
    SatelExtFlagDescription(
        key="verified_alarm",
        translation_key="partition_verified_alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.PARTITIONS_VERIFIED_ALARMS,
    ),
    SatelExtFlagDescription(
        key="warning_alarm",
        translation_key="partition_warning_alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        command=SatelExtReadCommand.PARTITIONS_WARNING_ALARMS,
    ),
)


@dataclass(frozen=True, kw_only=True)
class SatelIntegraSystemStatusBinarySensorEntityDescription(
    BinarySensorEntityDescription
):
    """Describes a Satel Integra system status binary sensor."""

    is_on_fn: Callable[[SatelIntegraSystemStatusData], bool | None]


def _has_system_trouble(
    troubles: SatelSystemTroubles | None, trouble: SatelTrouble
) -> bool | None:
    if troubles is None:
        return None
    return trouble in troubles.troubles


def _trouble(
    key: str,
    trouble_type: SatelTroubleType,
    *,
    source_id: int | None = None,
    translation_key: str | None = None,
    translation_placeholders: Mapping[str, str] | None = None,
    enabled: bool = False,
) -> SatelIntegraSystemStatusBinarySensorEntityDescription:
    trouble = SatelTrouble(trouble_type, source_id=source_id)
    return SatelIntegraSystemStatusBinarySensorEntityDescription(
        key=key,
        translation_key=translation_key or key,
        translation_placeholders=translation_placeholders,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
        is_on_fn=lambda data: _has_system_trouble(data.troubles, trouble),
    )


SYSTEM_STATUS_BINARY_SENSORS = (
    SatelIntegraSystemStatusBinarySensorEntityDescription(
        key="service_mode",
        translation_key="service_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data.status.service_mode if data.status else None,
    ),
    SatelIntegraSystemStatusBinarySensorEntityDescription(
        key="system_trouble",
        translation_key="system_trouble",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data.status.troubles if data.status else None,
    ),
    SatelIntegraSystemStatusBinarySensorEntityDescription(
        key="troubles_memory",
        translation_key="troubles_memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: data.status.troubles_memory if data.status else None,
    ),
    _trouble("panel_ac_trouble", SatelTroubleType.PANEL_AC, enabled=True),
    _trouble("panel_battery_trouble", SatelTroubleType.PANEL_BATTERY, enabled=True),
    _trouble("panel_battery_missing_trouble", SatelTroubleType.PANEL_BATTERY_MISSING),
    *(
        _trouble(
            f"output_{n}_trouble",
            SatelTroubleType.OUTPUT,
            source_id=n,
            translation_key="output_trouble",
            translation_placeholders={"number": str(n)},
        )
        for n in range(1, 5)
    ),
    _trouble("keypad_power_supply_trouble", SatelTroubleType.KEYPAD_POWER_SUPPLY),
    _trouble("expander_power_supply_trouble", SatelTroubleType.EXPANDER_POWER_SUPPLY),
    _trouble("dt1_trouble", SatelTroubleType.DT1),
    _trouble("dt2_trouble", SatelTroubleType.DT2),
    _trouble("dtm_trouble", SatelTroubleType.DTM),
    _trouble("rtc_trouble", SatelTroubleType.RTC),
    *(
        _trouble(
            f"monitoring_station_{n}_trouble",
            SatelTroubleType.MONITORING_STATION,
            source_id=n,
            translation_key="monitoring_station_trouble",
            translation_placeholders={"number": str(n)},
        )
        for n in (1, 2)
    ),
    _trouble("eeprom_or_rtc_access_trouble", SatelTroubleType.EEPROM_OR_RTC_ACCESS),
    _trouble("ram_trouble", SatelTroubleType.RAM),
    _trouble("panel_restart_memory_trouble", SatelTroubleType.PANEL_RESTART_MEMORY),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SatelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Satel Integra binary sensor devices."""

    runtime_data = config_entry.runtime_data

    async_add_entities(
        [
            SatelIntegraSystemStatusBinarySensor(
                runtime_data.coordinator_system_status,
                config_entry.entry_id,
                description,
            )
            for description in SYSTEM_STATUS_BINARY_SENSORS
        ]
    )

    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_ZONE):
        zone_num: int = subentry.data[CONF_ZONE_NUMBER]
        zone_type: BinarySensorDeviceClass = subentry.data[CONF_ZONE_TYPE]

        async_add_entities(
            [
                SatelIntegraBinarySensor(
                    runtime_data.coordinator_zones,
                    config_entry.entry_id,
                    subentry,
                    zone_num,
                    zone_type,
                ),
                *(
                    SatelIntegraZoneFlagBinarySensor(
                        runtime_data.coordinator_ext,
                        config_entry.entry_id,
                        subentry,
                        zone_num,
                        description,
                    )
                    for description in ZONE_FLAG_SENSORS
                ),
            ],
            config_subentry_id=subentry.subentry_id,
        )

    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_PARTITION):
        partition_num: int = subentry.data[CONF_PARTITION_NUMBER]
        async_add_entities(
            [
                SatelIntegraPartitionFlagBinarySensor(
                    runtime_data.coordinator_ext,
                    config_entry.entry_id,
                    subentry,
                    partition_num,
                    description,
                )
                for description in PARTITION_FLAG_SENSORS
            ],
            config_subentry_id=subentry.subentry_id,
        )

    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_OUTPUT):
        output_num: int = subentry.data[CONF_OUTPUT_NUMBER]
        output_type: BinarySensorDeviceClass = subentry.data[CONF_ZONE_TYPE]

        async_add_entities(
            [
                SatelIntegraBinarySensor(
                    runtime_data.coordinator_outputs,
                    config_entry.entry_id,
                    subentry,
                    output_num,
                    output_type,
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SatelIntegraBinarySensor[_CoordinatorT: SatelIntegraBaseCoordinator](
    SatelIntegraEntity[_CoordinatorT], BinarySensorEntity
):
    """Base binary sensor for Satel Integra."""

    _attr_name = None

    def __init__(
        self,
        coordinator: _CoordinatorT,
        config_entry_id: str,
        subentry: ConfigSubentry,
        device_number: int,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        """Initialize the binary_sensor."""
        super().__init__(coordinator, config_entry_id, subentry, device_number)
        self._attr_device_class = device_class
        self._attr_is_on = self._get_state_from_coordinator()

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self._get_state_from_coordinator()
        self.async_write_ha_state()

    def _get_state_from_coordinator(self) -> bool | None:
        """Method to get binary sensor state from coordinator data."""
        return self.coordinator.data.get(self._device_number)


class _SatelFlagBinarySensor(
    SatelIntegraEntity[SatelIntegraExtCoordinator], BinarySensorEntity
):
    """Zone/partition flag from the extended monitoring."""

    entity_description: SatelExtFlagDescription

    def __init__(
        self,
        coordinator: SatelIntegraExtCoordinator,
        config_entry_id: str,
        subentry: ConfigSubentry,
        device_number: int,
        description: SatelExtFlagDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, config_entry_id, subentry, device_number, description.key
        )
        self.entity_description = description

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the flag."""
        return self._flag()

    def _flag(self) -> bool | None:
        raise NotImplementedError


class SatelIntegraZoneFlagBinarySensor(_SatelFlagBinarySensor):
    """Zone tamper/alarm/... flag."""

    def _flag(self) -> bool | None:
        return self.coordinator.data.zone_flag(
            self.entity_description.command, self._device_number
        )


class SatelIntegraPartitionFlagBinarySensor(_SatelFlagBinarySensor):
    """Partition flag (violated zones, alarm memory, ...)."""

    def _flag(self) -> bool | None:
        return self.coordinator.data.partition_flag(
            self.entity_description.command, self._device_number
        )


class SatelIntegraSystemStatusBinarySensor(
    SatelIntegraBaseEntity[SatelIntegraSystemStatusCoordinator], BinarySensorEntity
):
    """Representation of a Satel Integra system status binary sensor."""

    entity_description: SatelIntegraSystemStatusBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: SatelIntegraSystemStatusCoordinator,
        config_entry_id: str,
        description: SatelIntegraSystemStatusBinarySensorEntityDescription,
    ) -> None:
        """Initialize the system status binary sensor."""
        super().__init__(coordinator, config_entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{config_entry_id}_{description.key}"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the state described by the entity description."""
        return self.entity_description.is_on_fn(self.coordinator.data)
