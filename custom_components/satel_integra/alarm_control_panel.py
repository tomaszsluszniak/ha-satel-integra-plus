"""Support for Satel Integra alarm, using ETHM module."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Any, override

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from satel_integra import AlarmState

from .const import (
    CONF_ALL_ARM_MODES,
    CONF_ALL_PARTITIONS,
    CONF_ALL_PARTITIONS_PANEL,
    CONF_ARM_HOME_MODE,
    CONF_PARTITION_NUMBER,
    CONF_USE_CODE_FOR_PANELS,
    SUBENTRY_TYPE_PARTITION,
)
from .coordinator import (
    SatelConfigEntry,
    SatelIntegraExtCoordinator,
    SatelIntegraPartitionsCoordinator,
)
from .entity import SatelIntegraBaseEntity, SatelIntegraEntity
from .helpers import async_validate_command, resolve_code
from .satel_ext import SatelExtReadCommand

ALARM_STATE_MAP = {
    AlarmState.TRIGGERED: AlarmControlPanelState.TRIGGERED,
    AlarmState.TRIGGERED_FIRE: AlarmControlPanelState.TRIGGERED,
    AlarmState.ENTRY_TIME: AlarmControlPanelState.PENDING,
    AlarmState.ARMED_MODE3: AlarmControlPanelState.ARMED_HOME,
    AlarmState.ARMED_MODE2: AlarmControlPanelState.ARMED_HOME,
    AlarmState.ARMED_MODE1: AlarmControlPanelState.ARMED_HOME,
    AlarmState.ARMED_MODE0: AlarmControlPanelState.ARMED_AWAY,
    AlarmState.EXIT_COUNTDOWN_OVER_10: AlarmControlPanelState.ARMING,
    AlarmState.EXIT_COUNTDOWN_UNDER_10: AlarmControlPanelState.ARMING,
}

# "All arming modes" option: every Satel mode has its own HA arming action/state
MODE_STATES = {
    0: AlarmControlPanelState.ARMED_AWAY,  # czuwanie pełne
    1: AlarmControlPanelState.ARMED_CUSTOM_BYPASS,  # pełne + blokady
    2: AlarmControlPanelState.ARMED_HOME,  # bez wewnętrznych
    3: AlarmControlPanelState.ARMED_NIGHT,  # bez wewnętrznych i bez czasu na wejście
}
MODE_ALARM_STATES = {
    0: AlarmState.ARMED_MODE0,
    1: AlarmState.ARMED_MODE1,
    2: AlarmState.ARMED_MODE2,
    3: AlarmState.ARMED_MODE3,
}

ARMED_STATES = set(MODE_STATES.values())

# Extra partition flags shown as attributes
PARTITION_ATTRIBUTES = {
    "violated_zones": SatelExtReadCommand.PARTITIONS_VIOLATED_ZONES,
    "alarm_memory": SatelExtReadCommand.PARTITIONS_ALARM_MEMORY,
    "fire_alarm_memory": SatelExtReadCommand.PARTITIONS_FIRE_ALARM_MEMORY,
    "first_code_entered": SatelExtReadCommand.PARTITIONS_FIRST_CODE_ENTERED,
    "temporary_blocked": SatelExtReadCommand.PARTITIONS_TEMPORARY_BLOCKED,
}

PARALLEL_UPDATES = 0


def partition_armed_mode(
    data: dict[AlarmState, list[int]], partition: int
) -> int | None:
    """Return the Satel arming mode (0-3) of a partition, None if not armed."""
    for mode in (3, 2, 1, 0):  # mode 1-3 partitions are also in the mode 0 list
        if partition in data.get(MODE_ALARM_STATES[mode], ()):
            return mode
    return None


def partition_alarm_state(
    data: dict[AlarmState, list[int]], partition: int, all_modes: bool = False
) -> AlarmControlPanelState:
    """Translate the panel state of one partition into a HA state."""
    for satel_state, ha_state in ALARM_STATE_MAP.items():
        if partition in data.get(satel_state, ()):
            if all_modes and ha_state in (
                AlarmControlPanelState.ARMED_AWAY,
                AlarmControlPanelState.ARMED_HOME,
            ):
                mode = partition_armed_mode(data, partition)
                return MODE_STATES[mode if mode is not None else 0]
            return ha_state
    return AlarmControlPanelState.DISARMED


def combined_alarm_state(
    states: Iterable[AlarmControlPanelState], all_modes: bool = False
) -> AlarmControlPanelState:
    """Combine states of several partitions into one."""
    states = list(states)
    for state in (
        AlarmControlPanelState.TRIGGERED,
        AlarmControlPanelState.PENDING,
        AlarmControlPanelState.ARMING,
    ):
        if state in states:
            return state
    armed = [state for state in states if state in ARMED_STATES]
    if not armed:
        return AlarmControlPanelState.DISARMED
    if all_modes:
        # The strongest mode among armed partitions; a partial arming is shown
        # by the `partially_armed` attribute (custom bypass is mode 1 here)
        for state in MODE_STATES.values():
            if state in armed:
                return state
    if len(armed) < len(states):
        # Part of the partitions armed - there is no "partially armed" state
        return AlarmControlPanelState.ARMED_CUSTOM_BYPASS
    if all(state == AlarmControlPanelState.ARMED_AWAY for state in armed):
        return AlarmControlPanelState.ARMED_AWAY
    return AlarmControlPanelState.ARMED_HOME


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SatelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up for Satel Integra alarm panels."""

    runtime_data = config_entry.runtime_data
    use_code = config_entry.options.get(CONF_USE_CODE_FOR_PANELS, False)
    all_modes = config_entry.options.get(CONF_ALL_ARM_MODES, True)

    partitions: dict[int, ConfigSubentry] = {}
    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_PARTITION):
        partition_num: int = subentry.data[CONF_PARTITION_NUMBER]
        partitions[partition_num] = subentry

        async_add_entities(
            [
                SatelIntegraAlarmPanel(
                    runtime_data.coordinator_partitions,
                    runtime_data.coordinator_ext,
                    config_entry.entry_id,
                    subentry,
                    partition_num,
                    subentry.data[CONF_ARM_HOME_MODE],
                    use_code,
                    all_modes,
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )

    if partitions and config_entry.options.get(CONF_ALL_PARTITIONS_PANEL, True):
        selected = [
            int(number)
            for number in config_entry.options.get(CONF_ALL_PARTITIONS) or []
            if int(number) in partitions
        ] or sorted(partitions)
        async_add_entities(
            [
                SatelIntegraAllPartitionsPanel(
                    runtime_data.coordinator_partitions,
                    runtime_data.coordinator_ext,
                    config_entry.entry_id,
                    {number: partitions[number] for number in sorted(selected)},
                    use_code,
                    all_modes,
                )
            ]
        )


class _SatelPanelMixin(AlarmControlPanelEntity):
    """Common code of the partition and the all-partitions panels."""

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )

    coordinator: SatelIntegraPartitionsCoordinator
    _ext_coordinator: SatelIntegraExtCoordinator
    _use_stored_code: bool
    _all_modes: bool

    _modes_translation_key: str

    def _setup_modes(self, all_modes: bool) -> None:
        self._all_modes = all_modes
        if all_modes:
            # state names of Satel modes (czuwanie pełne, ...)
            self._attr_translation_key = self._modes_translation_key
            self._attr_supported_features = (
                AlarmControlPanelEntityFeature.ARM_AWAY
                | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
                | AlarmControlPanelEntityFeature.ARM_HOME
                | AlarmControlPanelEntityFeature.ARM_NIGHT
            )

    async def _arm_action(self, code: str | None, mode: int | None) -> None:
        """Arm in a Satel mode; None = classic 'arm home' (per-partition mode)."""
        raise NotImplementedError

    @override
    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm in mode 0 (czuwanie pełne)."""
        await self._arm_action(code, 0)

    @override
    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Arm in mode 1 (pełne + blokady)."""
        await self._arm_action(code, 1)

    @override
    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm in mode 2 (bez wewnętrznych) or in the configured 'arm home' mode."""
        await self._arm_action(code, 2 if self._all_modes else None)

    @override
    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Arm in mode 3 (bez wewnętrznych i bez czasu na wejście)."""
        await self._arm_action(code, 3)

    def _setup_code(self, use_stored_code: bool) -> None:
        self._use_stored_code = use_stored_code
        if use_stored_code:
            self._attr_code_format = None
            self._attr_code_arm_required = False
        else:
            self._attr_code_format = CodeFormat.NUMBER

    def _code(self, code: str | None) -> str:
        stored = self.coordinator.client.stored_code if self._use_stored_code else None
        return resolve_code(code, stored)

    @override
    async def async_added_to_hass(self) -> None:
        """Also follow the extended state (attributes)."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._ext_coordinator.async_add_listener(self._handle_ext_update)
        )

    @callback
    def _handle_ext_update(self) -> None:
        self.async_write_ha_state()

    def _partition_flags(self, partition: int) -> dict[str, bool | None]:
        data = self._ext_coordinator.data
        return {
            name: data.partition_flag(command, partition)
            for name, command in PARTITION_ATTRIBUTES.items()
        }

    async def _arm(self, code: str | None, modes: dict[int, list[int]]) -> None:
        controller = self.coordinator.client.controller
        resolved = self._code(code)
        for mode, partitions in sorted(modes.items()):
            await async_validate_command(
                controller.arm(resolved, partitions, mode, wait_for_result=True)
            )

    async def _disarm(
        self, code: str | None, partitions: list[int], clear_alarm: bool
    ) -> None:
        controller = self.coordinator.client.controller
        resolved = self._code(code)
        await async_validate_command(
            controller.disarm(resolved, partitions, wait_for_result=True)
        )
        if clear_alarm:
            await async_validate_command(
                controller.clear_alarm(resolved, partitions, wait_for_result=True)
            )


class SatelIntegraAlarmPanel(
    SatelIntegraEntity[SatelIntegraPartitionsCoordinator], _SatelPanelMixin
):
    """Representation of a Satel Integra-based alarm panel (one partition)."""

    _attr_name = None
    _modes_translation_key = "partition"

    def __init__(
        self,
        coordinator: SatelIntegraPartitionsCoordinator,
        ext_coordinator: SatelIntegraExtCoordinator,
        config_entry_id: str,
        subentry: ConfigSubentry,
        device_number: int,
        arm_home_mode: int,
        use_stored_code: bool,
        all_modes: bool = True,
    ) -> None:
        """Initialize the alarm panel."""
        super().__init__(coordinator, config_entry_id, subentry, device_number)
        self._ext_coordinator = ext_coordinator
        self._arm_home_mode = int(arm_home_mode)
        self._setup_modes(all_modes)
        self._setup_code(use_stored_code)
        self._attr_alarm_state = self._read_alarm_state()

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_alarm_state = self._read_alarm_state()
        self.async_write_ha_state()

    def _read_alarm_state(self) -> AlarmControlPanelState:
        """Read current status of the alarm and translate it into HA status."""
        return partition_alarm_state(
            self.coordinator.data, self._device_number, self._all_modes
        )

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return partition details."""
        return {
            "partition_number": self._device_number,
            "arm_mode": partition_armed_mode(
                self.coordinator.data, self._device_number
            ),
            **self._partition_flags(self._device_number),
        }

    @override
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command (and clear the alarm if triggered)."""
        await self._disarm(
            code,
            [self._device_number],
            self._attr_alarm_state == AlarmControlPanelState.TRIGGERED,
        )

    async def _arm_action(self, code: str | None, mode: int | None) -> None:
        await self._arm(
            code, {self._arm_home_mode if mode is None else mode: [self._device_number]}
        )


class SatelIntegraAllPartitionsPanel(
    SatelIntegraBaseEntity[SatelIntegraPartitionsCoordinator], _SatelPanelMixin
):
    """One alarm panel controlling all (selected) partitions at once.

    Arming/disarming is sent as a single frame with all partitions, so the
    panel handles them at the same time (like a keypad "arm all").
    """

    _attr_translation_key = "all_partitions"
    _modes_translation_key = "all_partitions_modes"

    def __init__(
        self,
        coordinator: SatelIntegraPartitionsCoordinator,
        ext_coordinator: SatelIntegraExtCoordinator,
        config_entry_id: str,
        partitions: dict[int, ConfigSubentry],
        use_stored_code: bool,
        all_modes: bool = True,
    ) -> None:
        """Initialize the panel."""
        super().__init__(coordinator, config_entry_id)
        self._ext_coordinator = ext_coordinator
        self._attr_unique_id = f"{config_entry_id}_alarm_panel_all"
        self._partitions = list(partitions)
        self._names = {
            number: subentry.data[CONF_NAME] for number, subentry in partitions.items()
        }
        self._home_modes = {
            number: int(subentry.data[CONF_ARM_HOME_MODE])
            for number, subentry in partitions.items()
        }
        self._setup_modes(all_modes)
        self._setup_code(use_stored_code)
        self._attr_alarm_state = self._read_alarm_state()

    def _partition_states(self) -> dict[int, AlarmControlPanelState]:
        return {
            number: partition_alarm_state(
                self.coordinator.data, number, self._all_modes
            )
            for number in self._partitions
        }

    def _read_alarm_state(self) -> AlarmControlPanelState:
        return combined_alarm_state(self._partition_states().values(), self._all_modes)

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        self._attr_alarm_state = self._read_alarm_state()
        self.async_write_ha_state()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state of every partition."""
        states = self._partition_states()
        armed = [n for n, s in states.items() if s in ARMED_STATES]
        ext = self._ext_coordinator.data
        return {
            "partitions": {
                self._names[number]: {
                    "number": number,
                    "state": state.value,
                    "arm_mode": partition_armed_mode(self.coordinator.data, number),
                    **self._partition_flags(number),
                }
                for number, state in states.items()
            },
            "armed_partitions": [self._names[n] for n in armed],
            "disarmed_partitions": [
                self._names[n]
                for n, s in states.items()
                if s == AlarmControlPanelState.DISARMED
            ],
            "partially_armed": 0 < len(armed) < len(states),
            "ready_to_arm": not any(
                ext.partition_flag(SatelExtReadCommand.PARTITIONS_VIOLATED_ZONES, n)
                for n in self._partitions
            ),
        }

    @override
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm all partitions in one command, clear alarms if any."""
        triggered = any(
            state == AlarmControlPanelState.TRIGGERED
            for state in self._partition_states().values()
        )
        await self._disarm(code, self._partitions, triggered)

    async def _arm_action(self, code: str | None, mode: int | None) -> None:
        """Arm all partitions with one command (one per mode for classic home)."""
        if mode is not None:
            await self._arm(code, {mode: self._partitions})
            return
        modes: dict[int, list[int]] = defaultdict(list)
        for number in self._partitions:
            modes[self._home_modes[number]].append(number)
        await self._arm(code, dict(modes))
