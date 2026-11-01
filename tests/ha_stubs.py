"""Minimal stand-ins for Home Assistant modules (HA cannot be installed here).

Only what the integration imports is provided; behaviour is simplified, enough to
exercise the integration logic (entity states, attributes, service dispatch).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag, StrEnum
import sys
import types
from typing import Any


def _mod(name: str, **attrs: Any) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


def callback(func):
    return func


class HomeAssistantError(Exception):
    def __init__(
        self,
        *args,
        translation_domain=None,
        translation_key=None,
        translation_placeholders=None,
    ):
        super().__init__(translation_key or (args[0] if args else ""))
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders


class ServiceValidationError(HomeAssistantError):
    pass


class ConfigEntryError(HomeAssistantError):
    pass


class ConfigEntryNotReady(HomeAssistantError):
    pass


class Entity:
    hass = None
    entity_id = "test.entity"
    _attr_has_entity_name = False
    _attr_unique_id = None
    _attr_name = None
    _attr_supported_features = None
    _attr_extra_state_attributes = None
    entity_description = None
    written = 0

    def __init__(self, *args, **kwargs):
        pass

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def extra_state_attributes(self):
        return self._attr_extra_state_attributes

    def async_write_ha_state(self):
        self.written += 1

    def async_on_remove(self, func):
        pass

    async def async_added_to_hass(self):
        pass


class CoordinatorEntity(Entity):
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self):
        self.async_write_ha_state()


class DataUpdateCoordinator:
    def __init__(
        self, hass, logger, config_entry=None, name=None, update_interval=None
    ):
        self.hass = hass
        self.config_entry = config_entry
        self.last_update_success = True
        self._listeners = []

    def __class_getitem__(cls, item):
        return cls

    def async_set_updated_data(self, data):
        self.data = data
        self.async_update_listeners()

    def async_update_listeners(self):
        for listener in list(self._listeners):
            listener()

    def async_add_listener(self, func, context=None):
        self._listeners.append(func)
        return lambda: self._listeners.remove(func)

    async def async_refresh(self):
        self.data = await self._async_update_data()
        self.async_update_listeners()


class UpdateFailed(Exception):
    pass


class Debouncer:
    def __init__(self, hass, logger, cooldown, immediate, function):
        self.function = function

    def async_schedule_call(self):
        self.function()

    def async_shutdown(self):
        pass


class AlarmControlPanelState(StrEnum):
    DISARMED = "disarmed"
    ARMED_HOME = "armed_home"
    ARMED_AWAY = "armed_away"
    ARMED_NIGHT = "armed_night"
    ARMED_VACATION = "armed_vacation"
    ARMED_CUSTOM_BYPASS = "armed_custom_bypass"
    PENDING = "pending"
    ARMING = "arming"
    DISARMING = "disarming"
    TRIGGERED = "triggered"


class AlarmControlPanelEntityFeature(IntFlag):
    ARM_HOME = 1
    ARM_AWAY = 2
    ARM_NIGHT = 4
    ARM_CUSTOM_BYPASS = 16


class CodeFormat(StrEnum):
    TEXT = "text"
    NUMBER = "number"


class AlarmControlPanelEntity(Entity):
    _attr_code_format = None
    _attr_code_arm_required = True
    _attr_alarm_state = None

    @property
    def alarm_state(self):
        return self._attr_alarm_state


class BinarySensorDeviceClass(StrEnum):
    MOTION = "motion"
    DOOR = "door"
    TAMPER = "tamper"
    SAFETY = "safety"
    PROBLEM = "problem"


class BinarySensorEntity(Entity):
    _attr_is_on = None

    @property
    def is_on(self):
        return self._attr_is_on


class SwitchEntity(Entity):
    _attr_is_on = None

    @property
    def is_on(self):
        return self._attr_is_on


class EventEntity(Entity):
    def _trigger_event(self, event_type, attrs=None):
        assert event_type in self._attr_event_types, event_type
        self.triggered = getattr(self, "triggered", []) + [(event_type, attrs)]


@dataclass(frozen=True, kw_only=True)
class EntityDescription:
    key: str
    translation_key: str | None = None
    translation_placeholders: Any = None
    device_class: Any = None
    entity_category: Any = None
    entity_registry_enabled_default: bool = True
    name: Any = None


class EntityCategory(StrEnum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


class Platform(StrEnum):
    ALARM_CONTROL_PANEL = "alarm_control_panel"
    BINARY_SENSOR = "binary_sensor"
    EVENT = "event"
    SENSOR = "sensor"
    SWITCH = "switch"


class SupportsResponse(StrEnum):
    NONE = "none"
    ONLY = "only"


class ConfigEntryState(StrEnum):
    LOADED = "loaded"


class _Anything:
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Anything()

    def __getattr__(self, name):
        return _Anything()

    def __class_getitem__(cls, item):
        return cls


def install() -> None:
    import probatio_stub  # noqa: F401  (installs "probatio")

    _mod("homeassistant")
    _mod("homeassistant.components")
    _mod(
        "homeassistant.components.alarm_control_panel",
        AlarmControlPanelEntity=AlarmControlPanelEntity,
        AlarmControlPanelEntityFeature=AlarmControlPanelEntityFeature,
        AlarmControlPanelState=AlarmControlPanelState,
        CodeFormat=CodeFormat,
    )
    _mod(
        "homeassistant.components.binary_sensor",
        BinarySensorDeviceClass=BinarySensorDeviceClass,
        BinarySensorEntity=BinarySensorEntity,
        BinarySensorEntityDescription=EntityDescription,
    )
    _mod("homeassistant.components.switch", SwitchEntity=SwitchEntity)
    _mod("homeassistant.components.event", EventEntity=EventEntity)
    _mod(
        "homeassistant.components.sensor",
        SensorDeviceClass=_Anything(),
        SensorEntity=Entity,
        SensorStateClass=_Anything(),
    )
    _mod("homeassistant.components.frontend", add_extra_js_url=lambda hass, url: None)
    _mod("homeassistant.components.http", StaticPathConfig=_Anything)
    _mod("homeassistant.loader", async_get_integration=None)
    _mod("homeassistant.components.diagnostics", async_redact_data=lambda d, k: d)
    _mod(
        "homeassistant.config_entries",
        ConfigEntry=_Anything,
        ConfigEntryState=ConfigEntryState,
        ConfigFlow=type(
            "ConfigFlow", (), {"__init_subclass__": classmethod(lambda cls, **kw: None)}
        ),
        ConfigFlowResult=dict,
        ConfigSubentry=_Anything,
        ConfigSubentryFlow=object,
        OptionsFlow=object,
        SubentryFlowResult=dict,
    )
    _mod(
        "homeassistant.const",
        CONF_CODE="code",
        CONF_HOST="host",
        CONF_PORT="port",
        CONF_NAME="name",
        EVENT_HOMEASSISTANT_STOP="homeassistant_stop",
        EntityCategory=EntityCategory,
        Platform=Platform,
        UnitOfTemperature=_Anything(),
    )
    _mod(
        "homeassistant.core",
        HomeAssistant=object,
        Event=object,
        ServiceCall=object,
        ServiceResponse=dict,
        SupportsResponse=SupportsResponse,
        callback=callback,
    )
    _mod(
        "homeassistant.exceptions",
        HomeAssistantError=HomeAssistantError,
        ServiceValidationError=ServiceValidationError,
        ConfigEntryError=ConfigEntryError,
        ConfigEntryNotReady=ConfigEntryNotReady,
    )
    helpers = _mod("homeassistant.helpers")
    cv = _mod(
        "homeassistant.helpers.config_validation",
        removed=lambda *a, **k: None,
        string=str,
        boolean=bool,
        ensure_list=lambda v: v if isinstance(v, list) else [v],
    )
    dr = _mod(
        "homeassistant.helpers.device_registry",
        async_get_device_id_by_identifier=lambda *a, **k: "parent",
        DeviceInfo=dict,
        async_get=lambda hass: _Anything(),
    )
    selector = _mod("homeassistant.helpers.selector")
    selector.__getattr__ = lambda name: _Anything  # type: ignore[attr-defined]
    helpers.config_validation = cv
    helpers.device_registry = dr
    helpers.selector = selector
    _mod("homeassistant.helpers.entity_platform", AddConfigEntryEntitiesCallback=object)
    _mod(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=CoordinatorEntity,
        DataUpdateCoordinator=DataUpdateCoordinator,
        UpdateFailed=UpdateFailed,
    )
    _mod("homeassistant.helpers.debounce", Debouncer=Debouncer)
    _mod(
        "homeassistant.helpers.entity_registry",
        RegistryEntry=object,
        async_migrate_entries=None,
    )
    _mod("homeassistant.helpers.typing", ConfigType=dict)
