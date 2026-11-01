"""Support for Satel Integra devices."""

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.entity_registry import RegistryEntry, async_migrate_entries
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from satel_integra import SatelIntegraError

from .client import SatelClient
from .const import (
    CONF_ENABLE_TEMPERATURE_SENSOR,
    CONF_ENCRYPTION_KEY,
    CONF_EVENT_LOG_INTERVAL,
    CONF_OUTPUT_NUMBER,
    CONF_PARTITION_NUMBER,
    CONF_SWITCHABLE_OUTPUT_NUMBER,
    CONF_ZONE_NUMBER,
    DEFAULT_EVENT_LOG_INTERVAL,
    DOMAIN,
    SUBENTRY_TYPE_OUTPUT,
    SUBENTRY_TYPE_PARTITION,
    SUBENTRY_TYPE_SWITCHABLE_OUTPUT,
    SUBENTRY_TYPE_ZONE,
)
from .coordinator import (
    SatelConfigEntry,
    SatelIntegraData,
    SatelIntegraEventLogCoordinator,
    SatelIntegraExtCoordinator,
    SatelIntegraOutputsCoordinator,
    SatelIntegraPartitionsCoordinator,
    SatelIntegraSystemStatusCoordinator,
    SatelIntegraTemperaturesCoordinator,
    SatelIntegraZonesCoordinator,
)
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


CARD_URL = f"/{DOMAIN}/satel-alarm-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the service actions and the Lovelace card."""
    async_setup_services(hass)
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and load it in the frontend."""
    try:
        integration = await async_get_integration(hass, DOMAIN)
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_URL,
                    str(Path(__file__).parent / "www" / "satel-alarm-card.js"),
                    cache_headers=False,
                )
            ]
        )
        add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")
    except Exception:  # the integration works without the card
        _LOGGER.warning("Unable to register the Satel alarm card", exc_info=True)


async def async_setup_entry(hass: HomeAssistant, entry: SatelConfigEntry) -> bool:
    """Set up  Satel Integra from a config entry."""

    client = SatelClient(hass, entry)

    coordinator_zones = SatelIntegraZonesCoordinator(hass, entry, client)
    coordinator_outputs = SatelIntegraOutputsCoordinator(hass, entry, client)
    coordinator_partitions = SatelIntegraPartitionsCoordinator(hass, entry, client)
    coordinator_temperatures = SatelIntegraTemperaturesCoordinator(hass, entry, client)
    coordinator_system_status = SatelIntegraSystemStatusCoordinator(hass, entry, client)
    coordinator_ext = SatelIntegraExtCoordinator(hass, entry, client)
    coordinator_events = (
        SatelIntegraEventLogCoordinator(hass, entry, client)
        if entry.options.get(CONF_EVENT_LOG_INTERVAL, DEFAULT_EVENT_LOG_INTERVAL)
        else None
    )

    for coordinator in (
        coordinator_zones,
        coordinator_outputs,
        coordinator_partitions,
        coordinator_temperatures,
        coordinator_system_status,
        coordinator_ext,
    ):
        coordinator.setup()

    await client.async_connect()
    await coordinator_temperatures.async_config_entry_first_refresh()
    if coordinator_events is not None:
        await coordinator_events.async_refresh()

    try:
        panel_info = await client.controller.read_panel_info()
    except SatelIntegraError:
        _LOGGER.warning("Unable to read Satel panel information", exc_info=True)
        panel_info = None

    entry.runtime_data = SatelIntegraData(
        client=client,
        panel_info=panel_info,
        coordinator_zones=coordinator_zones,
        coordinator_outputs=coordinator_outputs,
        coordinator_partitions=coordinator_partitions,
        coordinator_temperatures=coordinator_temperatures,
        coordinator_system_status=coordinator_system_status,
        coordinator_ext=coordinator_ext,
        coordinator_events=coordinator_events,
    )

    async def async_close_connection(event: Event) -> None:
        """Close Satel Integra connection on HA Stop."""
        await client.async_close()

    entry.async_on_unload(entry.add_update_listener(update_listener))
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_connection)
    )

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Satel",
        model=panel_info.model.name if panel_info and panel_info.model else None,
        sw_version=str(panel_info.firmware) if panel_info else None,
        hw_version=(
            f"ETHM/INT-RS {client.module_info.firmware}" if client.module_info else None
        ),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SatelConfigEntry) -> bool:
    """Unloading the Satel platforms."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        runtime_data = entry.runtime_data
        await runtime_data.client.async_close()

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: SatelConfigEntry) -> None:
    """Handle options update."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: SatelConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    # 1.2 Migrate subentries to include configured numbers to title
    if config_entry.version == 1 and config_entry.minor_version == 1:
        for subentry in config_entry.subentries.values():
            property_map = {
                SUBENTRY_TYPE_PARTITION: CONF_PARTITION_NUMBER,
                SUBENTRY_TYPE_ZONE: CONF_ZONE_NUMBER,
                SUBENTRY_TYPE_OUTPUT: CONF_OUTPUT_NUMBER,
                SUBENTRY_TYPE_SWITCHABLE_OUTPUT: CONF_SWITCHABLE_OUTPUT_NUMBER,
            }

            prop = property_map[subentry.subentry_type]
            new_title = f"{subentry.title} ({subentry.data[prop]})"

            hass.config_entries.async_update_subentry(
                config_entry, subentry, title=new_title
            )

        hass.config_entries.async_update_entry(config_entry, minor_version=2)

    # 2.1 Migrate all entity unique IDs to replace "satel" prefix
    # with config entry ID, allows multiple entries to be configured
    if config_entry.version == 1:

        @callback
        def migrate_unique_id(entity_entry: RegistryEntry) -> dict[str, str]:
            """Migrate the unique ID to a new format."""
            return {
                "new_unique_id": entity_entry.unique_id.replace(
                    "satel", config_entry.entry_id
                )
            }

        await async_migrate_entries(hass, config_entry.entry_id, migrate_unique_id)
        hass.config_entries.async_update_entry(config_entry, version=2, minor_version=1)

    # 2.2 Added encryption key to config entry data
    if config_entry.version == 2 and config_entry.minor_version < 2:
        new_data = {**config_entry.data, CONF_ENCRYPTION_KEY: None}

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=2
        )

    # 2.3 Added temperature sensor option to zone subentries
    if config_entry.version == 2 and config_entry.minor_version < 3:
        for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_ZONE):
            hass.config_entries.async_update_subentry(
                config_entry,
                subentry,
                data={CONF_ENABLE_TEMPERATURE_SENSOR: False} | subentry.data,
            )

        hass.config_entries.async_update_entry(config_entry, minor_version=3)

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )

    return True
