"""Service actions of the Satel Integra integration."""

from __future__ import annotations

import probatio

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import SatelConfigEntry
from .helpers import async_validate_command, resolve_code

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_CODE = "code"
ATTR_PARTITIONS = "partitions"
ATTR_ZONES = "zones"
ATTR_OUTPUTS = "outputs"
ATTR_MODE = "mode"
ATTR_FORCE = "force"
ATTR_NO_BYPASS = "no_bypass"
ATTR_CLEAR_ALARM = "clear_alarm"
ATTR_ISOLATE = "isolate"
ATTR_STATE = "state"
ATTR_COUNT = "count"

SERVICE_ARM = "arm"
SERVICE_DISARM = "disarm"
SERVICE_CLEAR_ALARM = "clear_alarm"
SERVICE_BYPASS_ZONES = "bypass_zones"
SERVICE_UNBYPASS_ZONES = "unbypass_zones"
SERVICE_SET_OUTPUTS = "set_outputs"
SERVICE_CLEAR_TROUBLE_MEMORY = "clear_trouble_memory"
SERVICE_READ_EVENT_LOG = "read_event_log"

_NUMBERS = probatio.All(
    cv.ensure_list, [probatio.All(probatio.Coerce(int), probatio.Range(min=1, max=256))]
)
_PARTITIONS = probatio.All(
    cv.ensure_list, [probatio.All(probatio.Coerce(int), probatio.Range(min=1, max=32))]
)

_BASE = {
    probatio.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    probatio.Optional(ATTR_CODE): cv.string,
}

SCHEMAS = {
    SERVICE_ARM: probatio.Schema(
        {
            **_BASE,
            probatio.Optional(ATTR_PARTITIONS): _PARTITIONS,
            probatio.Optional(ATTR_MODE, default=0): probatio.All(
                probatio.Coerce(int), probatio.Range(min=0, max=3)
            ),
            probatio.Optional(ATTR_FORCE, default=False): cv.boolean,
            probatio.Optional(ATTR_NO_BYPASS, default=False): cv.boolean,
        }
    ),
    SERVICE_DISARM: probatio.Schema(
        {
            **_BASE,
            probatio.Optional(ATTR_PARTITIONS): _PARTITIONS,
            probatio.Optional(ATTR_CLEAR_ALARM, default=False): cv.boolean,
        }
    ),
    SERVICE_CLEAR_ALARM: probatio.Schema(
        {**_BASE, probatio.Optional(ATTR_PARTITIONS): _PARTITIONS}
    ),
    SERVICE_BYPASS_ZONES: probatio.Schema(
        {
            **_BASE,
            probatio.Required(ATTR_ZONES): _NUMBERS,
            probatio.Optional(ATTR_ISOLATE, default=False): cv.boolean,
        }
    ),
    SERVICE_UNBYPASS_ZONES: probatio.Schema(
        {**_BASE, probatio.Required(ATTR_ZONES): _NUMBERS}
    ),
    SERVICE_SET_OUTPUTS: probatio.Schema(
        {
            **_BASE,
            probatio.Required(ATTR_OUTPUTS): _NUMBERS,
            probatio.Required(ATTR_STATE): probatio.In(["on", "off", "toggle"]),
        }
    ),
    SERVICE_CLEAR_TROUBLE_MEMORY: probatio.Schema(_BASE),
    SERVICE_READ_EVENT_LOG: probatio.Schema(
        {
            probatio.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
            probatio.Optional(ATTR_COUNT, default=20): probatio.All(
                probatio.Coerce(int), probatio.Range(min=1, max=200)
            ),
        }
    ),
}


def _get_entry(hass: HomeAssistant, call: ServiceCall) -> SatelConfigEntry:
    entries: list[SatelConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_required"
            if not entry_id
            else "config_entry_not_loaded",
        )
    return entries[0]


def _partitions(entry: SatelConfigEntry, call: ServiceCall) -> list[int]:
    return call.data.get(ATTR_PARTITIONS) or entry.runtime_data.client.partitions


def _code(entry: SatelConfigEntry, call: ServiceCall) -> str:
    return resolve_code(call.data.get(ATTR_CODE), entry.runtime_data.client.stored_code)


async def _async_handle(call: ServiceCall) -> ServiceResponse:
    hass = call.hass
    entry = _get_entry(hass, call)
    controller = entry.runtime_data.client.controller
    service = call.service

    if service == SERVICE_READ_EVENT_LOG:
        events = await async_validate_command(
            controller.read_events(call.data[ATTR_COUNT])  # type: ignore[arg-type]
        )
        return {"events": [event.as_dict() for event in events or []]}

    code = _code(entry, call)
    if service == SERVICE_ARM:
        if call.data[ATTR_NO_BYPASS]:
            info = entry.runtime_data.client.module_info
            if info is not None and not info.supports_arm_no_bypass:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="no_bypass_unsupported"
                )
        await async_validate_command(
            controller.arm_ext(
                code,
                _partitions(entry, call),
                call.data[ATTR_MODE],
                force=call.data[ATTR_FORCE],
                no_bypass=call.data[ATTR_NO_BYPASS],
            )
        )
    elif service == SERVICE_DISARM:
        partitions = _partitions(entry, call)
        await async_validate_command(
            controller.disarm(code, partitions, wait_for_result=True)
        )
        if call.data[ATTR_CLEAR_ALARM]:
            await async_validate_command(
                controller.clear_alarm(code, partitions, wait_for_result=True)
            )
    elif service == SERVICE_CLEAR_ALARM:
        await async_validate_command(
            controller.clear_alarm(code, _partitions(entry, call), wait_for_result=True)
        )
    elif service == SERVICE_BYPASS_ZONES:
        await async_validate_command(
            controller.bypass_zones(
                code, call.data[ATTR_ZONES], isolate=call.data[ATTR_ISOLATE]
            )
        )
    elif service == SERVICE_UNBYPASS_ZONES:
        await async_validate_command(
            controller.bypass_zones(code, call.data[ATTR_ZONES], bypass=False)
        )
    elif service == SERVICE_SET_OUTPUTS:
        state = {"on": True, "off": False, "toggle": None}[call.data[ATTR_STATE]]
        await async_validate_command(
            controller.set_outputs(code, call.data[ATTR_OUTPUTS], state)
        )
    elif service == SERVICE_CLEAR_TROUBLE_MEMORY:
        await async_validate_command(controller.clear_trouble_memory(code))
    return None


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the service actions."""
    for service, schema in SCHEMAS.items():
        hass.services.async_register(
            DOMAIN,
            service,
            _async_handle,
            schema=schema,
            supports_response=SupportsResponse.ONLY
            if service == SERVICE_READ_EVENT_LOG
            else SupportsResponse.NONE,
        )
