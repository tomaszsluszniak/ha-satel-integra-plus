"""Extensions of the satel_integra library used by this integration.

The library (satel-integra 1.6.x) covers only part of the INT-RS /
ETHM-1 protocol. This module adds, without forking the library:

* monitoring of additional state commands (zone tamper/alarm/bypass/...,
  partition alarm memory, partitions with violated zones, ...),
* force arming (0xA0..0xA3) and arming without bypasses / exit delay,
* zone bypass, unbypass and isolate (0x86, 0x87, 0x90),
* outputs on/off/switch with a 16-byte mask (0x88, 0x89, 0x91),
* clearing the trouble memory (0x8B),
* reading the event log (0x8C) with event texts (0x8F) and device names (0xEE),
* fixes for library issues found during review (see `_apply_library_fixes`).

It depends on library internals, so the manifest allows only the 1.6.x series.
Hassfest rejects an exact pin of a package Home Assistant depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import unique
import logging
from typing import Any

from satel_integra import (
    AsyncSatel,
    SatelCommandResult,
    SatelMonitoringStartError,
    SatelNotConnectedError,
    queue as _satel_queue,
)
from satel_integra.callbacks import CallbackRegistry, StateChangeCallback
from satel_integra.commands import (
    SatelBaseCommand,
    SatelReadCommand,
    SatelWriteCommand,
)
from satel_integra.const import (
    FRAME_END,
    FRAME_SPECIAL_BYTES,
    FRAME_SPECIAL_BYTES_REPLACEMENT,
    FRAME_START,
)
from satel_integra.exceptions import (
    SatelCommandRejectedError,
    SatelUnexpectedResponseError,
)
from satel_integra.messages import SatelReadMessage, SatelWriteMessage
from satel_integra.transport import SatelEncryptedTransport
from satel_integra.utils import checksum, decode_bitmask_le, encode_bitmask_le

_LOGGER = logging.getLogger(__name__)


@unique
class SatelExtReadCommand(SatelBaseCommand):
    """Read commands the library does not know (values must not collide)."""

    ZONES_TAMPER = 0x01
    ZONES_ALARM = 0x02
    ZONES_TAMPER_ALARM = 0x03
    ZONES_ALARM_MEMORY = 0x04
    ZONES_TAMPER_ALARM_MEMORY = 0x05
    ZONES_BYPASS = 0x06
    ZONES_NO_VIOLATION_TROUBLE = 0x07
    ZONES_LONG_VIOLATION_TROUBLE = 0x08
    PARTITIONS_FIRST_CODE_ENTERED = 0x0D
    PARTITIONS_TEMPORARY_BLOCKED = 0x11
    PARTITIONS_GUARD_ROUND_BLOCKED = 0x12
    PARTITIONS_ALARM_MEMORY = 0x15
    PARTITIONS_FIRE_ALARM_MEMORY = 0x16
    PARTITIONS_VIOLATED_ZONES = 0x25
    ZONES_ISOLATE = 0x26
    PARTITIONS_VERIFIED_ALARMS = 0x27
    ZONES_MASKED = 0x28
    ZONES_MASKED_MEMORY = 0x29
    PARTITIONS_WARNING_ALARMS = 0x2B
    EVENT_TEXT = 0x8F


@unique
class SatelExtWriteCommand(SatelBaseCommand):
    """Control commands the library does not know."""

    ZONES_BYPASS = 0x86
    ZONES_UNBYPASS = 0x87
    OUTPUTS_ON = 0x88
    OUTPUTS_OFF = 0x89
    CLEAR_TROUBLE_MEMORY = 0x8B
    ZONES_ISOLATE = 0x90
    OUTPUTS_SWITCH = 0x91
    FORCE_ARM_MODE_0 = 0xA0
    FORCE_ARM_MODE_1 = 0xA1
    FORCE_ARM_MODE_2 = 0xA2
    FORCE_ARM_MODE_3 = 0xA3
    ARM_MODE_0 = 0x80
    ARM_MODE_1 = 0x81
    ARM_MODE_2 = 0x82
    ARM_MODE_3 = 0x83


ZONE_COMMANDS = frozenset(
    {
        SatelExtReadCommand.ZONES_TAMPER,
        SatelExtReadCommand.ZONES_ALARM,
        SatelExtReadCommand.ZONES_TAMPER_ALARM,
        SatelExtReadCommand.ZONES_ALARM_MEMORY,
        SatelExtReadCommand.ZONES_TAMPER_ALARM_MEMORY,
        SatelExtReadCommand.ZONES_BYPASS,
        SatelExtReadCommand.ZONES_NO_VIOLATION_TROUBLE,
        SatelExtReadCommand.ZONES_LONG_VIOLATION_TROUBLE,
        SatelExtReadCommand.ZONES_ISOLATE,
        SatelExtReadCommand.ZONES_MASKED,
        SatelExtReadCommand.ZONES_MASKED_MEMORY,
    }
)

PARTITION_COMMANDS = frozenset(
    {
        SatelExtReadCommand.PARTITIONS_FIRST_CODE_ENTERED,
        SatelExtReadCommand.PARTITIONS_TEMPORARY_BLOCKED,
        SatelExtReadCommand.PARTITIONS_GUARD_ROUND_BLOCKED,
        SatelExtReadCommand.PARTITIONS_ALARM_MEMORY,
        SatelExtReadCommand.PARTITIONS_FIRE_ALARM_MEMORY,
        SatelExtReadCommand.PARTITIONS_VIOLATED_ZONES,
        SatelExtReadCommand.PARTITIONS_VERIFIED_ALARMS,
        SatelExtReadCommand.PARTITIONS_WARNING_ALARMS,
    }
)

# Commands monitored by the library 1.6.0 (copied from AsyncSatel.start_monitoring)
_LIBRARY_MONITORED_COMMANDS = (
    SatelReadCommand.ZONES_VIOLATED,
    SatelReadCommand.PARTITIONS_ARMED_MODE0,
    SatelReadCommand.PARTITIONS_ARMED_MODE1,
    SatelReadCommand.PARTITIONS_ARMED_MODE2,
    SatelReadCommand.PARTITIONS_ARMED_MODE3,
    SatelReadCommand.PARTITIONS_ARMED_SUPPRESSED,
    SatelReadCommand.PARTITIONS_ENTRY_TIME,
    SatelReadCommand.PARTITIONS_EXIT_COUNTDOWN_OVER_10,
    SatelReadCommand.PARTITIONS_EXIT_COUNTDOWN_UNDER_10,
    SatelReadCommand.PARTITIONS_ALARM,
    SatelReadCommand.PARTITIONS_FIRE_ALARM,
    SatelReadCommand.OUTPUTS_STATE,
    SatelReadCommand.RTC_AND_STATUS,
    SatelReadCommand.TROUBLES_PART_1,
)

EXT_CONTROL_COMMANDS = frozenset(
    {
        SatelExtWriteCommand.ZONES_BYPASS,
        SatelExtWriteCommand.ZONES_UNBYPASS,
        SatelExtWriteCommand.OUTPUTS_ON,
        SatelExtWriteCommand.OUTPUTS_OFF,
        SatelExtWriteCommand.CLEAR_TROUBLE_MEMORY,
        SatelExtWriteCommand.ZONES_ISOLATE,
        SatelExtWriteCommand.OUTPUTS_SWITCH,
        SatelExtWriteCommand.FORCE_ARM_MODE_0,
        SatelExtWriteCommand.FORCE_ARM_MODE_1,
        SatelExtWriteCommand.FORCE_ARM_MODE_2,
        SatelExtWriteCommand.FORCE_ARM_MODE_3,
    }
)

# Arming without zone bypasses and without exit delay (INT-RS Plus >= 2.19, 0x7C bit 2)
ARM_FLAG_NO_BYPASS = 0x80

EVENT_CLASSES = {
    0: "zone_alarm",
    1: "partition_alarm",
    2: "arming",
    3: "bypass",
    4: "access_control",
    5: "trouble",
    6: "user_function",
    7: "system",
}

# Kinds of long description (Appendix 2) that carry a zone in the source field
_EVENT_KIND_ZONE = {1, 4, 32}
# ... and a user
_EVENT_KIND_USER = {2, 3, 6, 7}
# ... and a partition in PPPPP (other kinds keep e.g. a keypad or telephone there)
_EVENT_KIND_PARTITION = {1, 2, 5, 11, 12, 13, 15, 32}

_DEVICE_TYPE_ZONE = 1
_DEVICE_TYPE_USER = 2
_DEVICE_TYPE_PARTITION = 0


def _apply_library_fixes() -> None:
    """Patch defects of satel-integra 1.6.0 that affect the integration.

    1. SatelEncryptedTransport read the PDU with StreamReader.read(n), which may
       return fewer than n bytes when TCP splits the PDU. The truncated PDU then
       fails to decrypt and the connection is dropped. Use readexactly().
    2. Control commands added here must get the same protection as the
       library's own ones (never sent late, never sent after a reconnection).
    3. Responses to read commands added here must be matched by the queue.
    """
    if getattr(_apply_library_fixes, "done", False):
        return

    async def _read_from_transport(self: SatelEncryptedTransport) -> bytes | None:
        if not self._reader:
            return None
        data_len_bytes = await self._reader.readexactly(1)
        return await self._reader.readexactly(data_len_bytes[0])

    SatelEncryptedTransport._read_from_transport = _read_from_transport  # type: ignore[method-assign]

    _satel_queue.CONTROL_COMMANDS = frozenset(
        _satel_queue.CONTROL_COMMANDS | EXT_CONTROL_COMMANDS
    )

    original_expected = _satel_queue.expected_response_command

    def _expected_response_command(command: Any) -> Any:
        if isinstance(command, SatelExtReadCommand):
            return command
        return original_expected(command)

    _satel_queue.expected_response_command = _expected_response_command
    _apply_library_fixes.done = True  # type: ignore[attr-defined]


_apply_library_fixes()


def _decode_ext_frame(data: bytes) -> SatelReadMessage | None:
    """Decode a frame carrying one of SatelExtReadCommand, or return None."""
    if data[0:2] != FRAME_START or data[-2:] != FRAME_END:
        return None
    output = data[2:-2].replace(FRAME_SPECIAL_BYTES_REPLACEMENT, FRAME_SPECIAL_BYTES)
    if len(output) < 3:
        return None
    try:
        cmd = SatelExtReadCommand(output[0])
    except ValueError:
        return None
    if checksum(output[:-2]) != (output[-2] << 8) | output[-1]:
        # Let the library report the checksum error
        return None
    return SatelReadMessage(cmd, bytearray(output[1:-2]))


def _encode_code(code: str) -> bytes:
    """Encode a user code (with optional prefix) into 8 bytes."""
    code = code.strip()
    if not code.isdigit() or not 4 <= len(code) <= 16:
        raise ValueError("code must contain between 4 and 16 digits")
    return bytes.fromhex(code.ljust(16, "F"))


def _device_mask(numbers: list[int]) -> bytes:
    """Encode zones/outputs; 16 bytes unless a number above 128 is used.

    The library always sends 32 bytes, which INT-RS v1.x / ETHM-1 (not Plus)
    reject (wrong data length -> frame silently dropped).
    """
    if not numbers:
        raise ValueError("at least one zone/output is required")
    if min(numbers) < 1 or max(numbers) > 256:
        raise ValueError("zone/output number must be between 1 and 256")
    return encode_bitmask_le(sorted(set(numbers)), 32 if max(numbers) > 128 else 16)


def _partition_mask(partitions: list[int]) -> bytes:
    if not partitions:
        raise ValueError("at least one partition is required")
    if min(partitions) < 1 or max(partitions) > 32:
        raise ValueError("partition number must be between 1 and 32")
    return encode_bitmask_le(sorted(set(partitions)), 4)


@dataclass
class SatelExtState:
    """State of the additionally monitored commands."""

    zones: dict[SatelExtReadCommand, set[int]] = field(default_factory=dict)
    partitions: dict[SatelExtReadCommand, set[int]] = field(default_factory=dict)

    def zone_flag(self, command: SatelExtReadCommand, zone: int) -> bool | None:
        """Return the flag for a zone, None when not reported yet."""
        if command not in self.zones:
            return None
        return zone in self.zones[command]

    def partition_flag(
        self, command: SatelExtReadCommand, partition: int
    ) -> bool | None:
        """Return the flag for a partition, None when not reported yet."""
        if command not in self.partitions:
            return None
        return partition in self.partitions[command]


@dataclass(frozen=True)
class SatelEvent:
    """One record of the panel event log."""

    index: int
    timestamp: datetime | None
    event_class: str
    code: int
    restore: bool
    partition: int
    source: int
    object_number: int
    user_control_number: int
    kind: int | None = None
    text: str | None = None
    source_name: str | None = None
    partition_name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return {
            "index": self.index,
            "time": self.timestamp.isoformat() if self.timestamp else None,
            "class": self.event_class,
            "code": self.code,
            "restore": self.restore,
            "text": self.text,
            "partition": self.partition,
            "partition_name": self.partition_name,
            "source": self.source,
            "source_name": self.source_name,
            "kind": self.kind,
            "object": self.object_number,
        }


def _event_year(year_marker: int, month: int, day: int, now: datetime) -> int:
    """Return the most recent year matching YEAR mod 4 not later than now."""
    year = now.year - ((now.year - year_marker) % 4)
    try:
        if datetime(year, month, day) > now.replace(tzinfo=None):
            year -= 4
    except ValueError:
        pass
    return year


def decode_event_record(
    record: bytes, index: int, now: datetime | None = None
) -> SatelEvent | None:
    """Decode an 8-byte event record; None for the 'end of events' record."""
    b = record
    if not b[0] & 0x20:  # Z bit - record not empty
        return None
    now = now or datetime.now()
    year_marker = b[0] >> 6
    event_class = (b[1] >> 5) & 0x07
    day = b[1] & 0x1F
    month = b[2] >> 4
    minutes = ((b[2] & 0x0F) << 8) | b[3]
    partition = b[4] >> 3
    restore = bool(b[4] & 0x04)
    code = ((b[4] & 0x03) << 8) | b[5]
    source = b[6]
    object_number = b[7] >> 5
    user_control_number = b[7] & 0x1F

    timestamp: datetime | None
    try:
        timestamp = datetime(
            _event_year(year_marker, month, day, now),
            month,
            day,
            minutes // 60,
            minutes % 60,
        )
    except ValueError:
        timestamp = None

    return SatelEvent(
        index=index,
        timestamp=timestamp,
        event_class=EVENT_CLASSES[event_class],
        code=code,
        restore=restore,
        partition=partition,
        source=source,
        object_number=object_number,
        user_control_number=user_control_number,
    )


def _decode_name(raw: bytes) -> str:
    return raw.decode("cp1250", errors="replace").strip()


class SatelExtended(AsyncSatel):
    """AsyncSatel with additional protocol features."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the extended client."""
        super().__init__(*args, **kwargs)
        self.ext_state = SatelExtState()
        self._ext_callbacks = CallbackRegistry()
        self._event_texts: dict[int, tuple[int, str]] = {}
        self._names: dict[tuple[int, int], str | None] = {}
        for command in ZONE_COMMANDS:
            self._message_handlers[command] = self._ext_zones  # type: ignore[index]
        for command in PARTITION_COMMANDS:
            self._message_handlers[command] = self._ext_partitions  # type: ignore[index]

    # region monitoring
    async def start_monitoring(self) -> None:
        """Start monitoring of library and additional commands."""
        generation = self._connection.generation
        commands = [*_LIBRARY_MONITORED_COMMANDS, *ZONE_COMMANDS, *PARTITION_COMMANDS]
        bitmask = encode_bitmask_le([int(cmd) + 1 for cmd in commands], 12)
        msg = SatelWriteMessage(
            SatelWriteCommand.START_MONITORING, raw_data=bytearray(bitmask)
        )
        try:
            result = await self._send_data_and_wait(msg, SatelCommandResult)
        except (SatelCommandRejectedError, SatelUnexpectedResponseError) as err:
            raise SatelMonitoringStartError(
                "Monitoring startup did not receive a successful acknowledgement"
            ) from err
        if result is None:
            raise SatelMonitoringStartError("No response to monitoring request")

        was_ready = self.monitoring_ready
        self._monitoring_generation = generation
        if not was_ready and self.monitoring_ready:
            await self._connection.notify_state_changed()
        _LOGGER.debug("Extended monitoring started")

    async def _read_data(self) -> SatelReadMessage | None:
        """Read a frame, decoding the additional commands first."""
        try:
            data = await self._connection.read_frame()
            if not data:
                return None
            if (msg := _decode_ext_frame(data)) is not None:
                return msg
            return SatelReadMessage.decode_frame(data)
        except Exception as err:  # noqa: BLE001 - same as the library
            _LOGGER.warning("Dropping undecodable frame: %s", err)
            return None

    def _ext_zones(self, msg: SatelReadMessage) -> None:
        length = len(msg.msg_data) if len(msg.msg_data) in (16, 32) else 32
        zones = set(msg.get_active_bits(length))
        command = SatelExtReadCommand(int(msg.cmd))
        if self.ext_state.zones.get(command) == zones:
            return
        self.ext_state.zones[command] = zones
        _LOGGER.debug("%s: %s", command.name, sorted(zones))
        self._ext_callbacks.notify()

    def _ext_partitions(self, msg: SatelReadMessage) -> None:
        partitions = set(msg.get_active_bits(4))
        command = SatelExtReadCommand(int(msg.cmd))
        if self.ext_state.partitions.get(command) == partitions:
            return
        self.ext_state.partitions[command] = partitions
        _LOGGER.debug("%s: %s", command.name, sorted(partitions))
        self._ext_callbacks.notify()

    def add_ext_state_callback(self, callback: StateChangeCallback):
        """Subscribe to changes of the additionally monitored state."""
        return self._ext_callbacks.add(callback)

    # endregion

    # region control
    def _ensure_connected(self, command: SatelBaseCommand) -> None:
        if not self.connected:
            raise SatelNotConnectedError(
                f"Not connected to the panel, {command} was not sent"
            )

    async def _control(
        self, command: SatelBaseCommand, payload: bytes
    ) -> SatelCommandResult:
        self._ensure_connected(command)
        msg = SatelWriteMessage(command, raw_data=bytearray(payload))  # type: ignore[arg-type]
        result = await self._send_control_message(msg, True)
        assert result is not None
        return result

    async def arm_ext(
        self,
        code: str,
        partitions: list[int],
        mode: int = 0,
        *,
        force: bool = False,
        no_bypass: bool = False,
    ) -> SatelCommandResult:
        """Arm partitions, optionally forced and/or without bypasses/exit delay."""
        if not 0 <= mode <= 3:
            raise ValueError("mode must be between 0 and 3")
        base = (
            SatelExtWriteCommand.FORCE_ARM_MODE_0
            if force
            else SatelExtWriteCommand.ARM_MODE_0
        )
        command = SatelExtWriteCommand(int(base) + mode)
        payload = _encode_code(code) + _partition_mask(partitions)
        if no_bypass:
            payload += bytes([ARM_FLAG_NO_BYPASS])
        if not force and not no_bypass:
            # Plain arming: use the library (grouping with concurrent commands)
            result = await self.arm(code, partitions, mode, wait_for_result=True)
            assert result is not None
            return result
        return await self._control(command, payload)

    async def bypass_zones(
        self, code: str, zones: list[int], *, bypass: bool = True, isolate: bool = False
    ) -> SatelCommandResult:
        """Bypass, isolate or unbypass zones."""
        if isolate:
            command = SatelExtWriteCommand.ZONES_ISOLATE
        elif bypass:
            command = SatelExtWriteCommand.ZONES_BYPASS
        else:
            command = SatelExtWriteCommand.ZONES_UNBYPASS
        return await self._control(command, _encode_code(code) + _device_mask(zones))

    async def set_outputs(
        self, code: str, outputs: list[int], state: bool | None
    ) -> SatelCommandResult:
        """Turn outputs on (True), off (False) or toggle them (None) in one frame."""
        if state is None:
            command = SatelExtWriteCommand.OUTPUTS_SWITCH
        elif state:
            command = SatelExtWriteCommand.OUTPUTS_ON
        else:
            command = SatelExtWriteCommand.OUTPUTS_OFF
        return await self._control(command, _encode_code(code) + _device_mask(outputs))

    async def clear_trouble_memory(self, code: str) -> SatelCommandResult:
        """Clear the trouble memory."""
        return await self._control(
            SatelExtWriteCommand.CLEAR_TROUBLE_MEMORY, _encode_code(code)
        )

    # endregion

    # region event log
    async def _read_event_raw(self, index: bytes) -> tuple[bytes, int] | None:
        msg = SatelWriteMessage(SatelReadCommand.READ_EVENT, raw_data=bytearray(index))
        response = await self._send_data_and_wait(msg)
        if response is None or response.cmd != SatelReadCommand.READ_EVENT:
            return None
        data = bytes(response.msg_data)
        if len(data) < 11:
            raise SatelUnexpectedResponseError(f"Invalid event record: {data.hex()}")
        return data[:8], int.from_bytes(data[8:11], "big")

    async def read_last_event_index(self) -> int | None:
        """Return the index of the newest event, None if the log is empty."""
        raw = await self._read_event_raw(b"\xff\xff\xff")
        if raw is None or not raw[0][0] & 0x20:
            return None
        return raw[1]

    async def read_events(
        self,
        count: int,
        *,
        stop_at_index: int | None = None,
        with_texts: bool = True,
    ) -> list[SatelEvent]:
        """Read up to `count` newest events (newest first).

        Stops before `stop_at_index` (already known event) if given.
        """
        events: list[SatelEvent] = []
        index_bytes = b"\xff\xff\xff"
        now = datetime.now()
        for _ in range(count):
            raw = await self._read_event_raw(index_bytes)
            if raw is None:
                break
            record, index = raw
            if stop_at_index is not None and index == stop_at_index:
                break
            event = decode_event_record(record, index, now)
            if event is None:
                break
            events.append(event)
            index_bytes = index.to_bytes(3, "big")

        if with_texts:
            events = [await self._describe_event(event) for event in events]
        return events

    async def _describe_event(self, event: SatelEvent) -> SatelEvent:
        try:
            kind, text = await self.read_event_text(event.code, event.restore)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Cannot read text of event %s: %s", event.code, err)
            return event

        source_name = None
        if kind in _EVENT_KIND_ZONE and 1 <= event.source <= 128:
            source = event.source + (128 if event.user_control_number == 1 else 0)
            source_name = await self.read_device_name(_DEVICE_TYPE_ZONE, source)
        elif kind in _EVENT_KIND_USER and event.source:
            source_name = await self.read_device_name(_DEVICE_TYPE_USER, event.source)
        partition_name = (
            await self.read_device_name(_DEVICE_TYPE_PARTITION, event.partition)
            if kind in _EVENT_KIND_PARTITION and event.partition
            else None
        )

        return SatelEvent(
            **{
                **event.__dict__,
                "kind": kind,
                "text": text,
                "source_name": source_name,
                "partition_name": partition_name,
            }
        )

    async def read_event_text(self, code: int, restore: bool) -> tuple[int, str]:
        """Return (kind of long description, long text) of an event code."""
        key = (int(restore) << 10) | code
        if key in self._event_texts:
            return self._event_texts[key]
        request = (0x8000 | key).to_bytes(2, "big")
        msg = SatelWriteMessage(
            SatelExtReadCommand.EVENT_TEXT,  # type: ignore[arg-type]
            raw_data=bytearray(request),
        )
        response = await self._send_data_and_wait(msg)
        if response is None or len(response.msg_data) < 6:
            raise SatelUnexpectedResponseError("No event text received")
        data = bytes(response.msg_data)
        result = (data[2], _decode_name(data[5:]))
        self._event_texts[key] = result
        return result

    async def read_device_name(self, device_type: int, number: int) -> str | None:
        """Read (and cache) a device name using 0xEE."""
        key = (device_type, number)
        if key in self._names:
            return self._names[key]
        name: str | None = None
        try:
            msg = SatelWriteMessage(
                SatelReadCommand.READ_DEVICE_NAME,
                raw_data=bytearray([device_type, number & 0xFF]),
            )
            response = await self._send_data_and_wait(msg)
            if response is not None and len(response.msg_data) >= 19:
                name = _decode_name(bytes(response.msg_data[3:19])) or None
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "Cannot read name of device %s/%s: %s", device_type, number, err
            )
        self._names[key] = name
        return name

    # endregion

    async def read_module_info(self):
        """Read the communication module info, None on failure."""
        try:
            return await self.read_communication_module_info()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Cannot read module info: %s", err)
            return None


__all__ = [
    "SatelEvent",
    "SatelExtReadCommand",
    "SatelExtState",
    "SatelExtWriteCommand",
    "SatelExtended",
    "decode_bitmask_le",
    "decode_event_record",
]
