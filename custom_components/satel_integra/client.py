"""Satel Integra client."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CODE, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from satel_integra.exceptions import (
    SatelConnectFailedError,
    SatelConnectionInitializationError,
    SatelMonitoringStartError,
    SatelPanelBusyError,
)

from .const import (
    CONF_ENCRYPTION_KEY,
    CONF_OUTPUT_NUMBER,
    CONF_PARTITION_NUMBER,
    CONF_SWITCHABLE_OUTPUT_NUMBER,
    CONF_ZONE_NUMBER,
    DOMAIN,
    SUBENTRY_TYPE_OUTPUT,
    SUBENTRY_TYPE_PARTITION,
    SUBENTRY_TYPE_SWITCHABLE_OUTPUT,
    SUBENTRY_TYPE_ZONE,
)
from .satel_ext import SatelExtended

_LOGGER = logging.getLogger(__name__)


class SatelClient:
    """Client to connect to Satel Integra."""

    controller: SatelExtended

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the client wrapper."""
        self.hass = hass
        self.config_entry = entry

        host = entry.data[CONF_HOST]
        port = entry.data[CONF_PORT]

        self.partitions: list[int] = sorted(
            subentry.data[CONF_PARTITION_NUMBER]
            for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_PARTITION)
        )

        zones = [
            subentry.data[CONF_ZONE_NUMBER]
            for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_ZONE)
        ]

        outputs = [
            subentry.data[CONF_OUTPUT_NUMBER]
            for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_OUTPUT)
        ]

        switchable_outputs = [
            subentry.data[CONF_SWITCHABLE_OUTPUT_NUMBER]
            for subentry in entry.get_subentries_of_type(
                SUBENTRY_TYPE_SWITCHABLE_OUTPUT
            )
        ]

        self.controller = SatelExtended(
            host,
            port,
            zones,
            outputs + switchable_outputs,
            self.partitions,
            integration_key=entry.data.get(CONF_ENCRYPTION_KEY),
        )
        self.module_info = None

    @property
    def stored_code(self) -> str | None:
        """Return the user code stored in the integration options."""
        return self.config_entry.options.get(CONF_CODE) or None

    async def async_connect(self) -> None:
        """Start controller connection."""
        try:
            await self.controller.connect(raise_exceptions=True)
        except SatelConnectFailedError as ex:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
            ) from ex
        except SatelPanelBusyError as ex:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="panel_busy",
            ) from ex
        except SatelConnectionInitializationError as ex:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="connection_initialization_failed",
            ) from ex

        try:
            await self.controller.start(enable_monitoring=True)
        except SatelMonitoringStartError as ex:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="monitoring_start_failed",
            ) from ex

        self.module_info = await self.controller.read_module_info()

    async def async_close(self) -> None:
        """Close the connection."""
        await self.controller.close()
