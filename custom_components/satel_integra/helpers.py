"""Helpers for Satel Integra commands."""

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from satel_integra import (
    SatelCommandExpiredError,
    SatelCommandRejectedError,
    SatelCommandResult,
    SatelIntegraError,
    SatelNoResponseError,
    SatelNotConnectedError,
    SatelResultCode,
)

from .const import DOMAIN

_REJECTION_KEYS = {
    SatelResultCode.USER_CODE_NOT_FOUND: "command_rejected_wrong_code",
    SatelResultCode.NO_ACCESS: "command_rejected_no_access",
    SatelResultCode.CANNOT_ARM_CAN_FORCE: "command_rejected_can_force",
    SatelResultCode.CANNOT_ARM: "command_rejected_cannot_arm",
}


def resolve_code(code: str | None, stored_code: str | None) -> str:
    """Return the code to use, falling back to the stored one."""
    code = code or stored_code
    if not code:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="missing_alarm_access_code"
        )
    if not code.isdigit() or not 4 <= len(code) <= 16:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="invalid_code_format"
        )
    return code


async def async_validate_command(
    command: Awaitable[SatelCommandResult | None],
) -> SatelCommandResult | None:
    """Run a panel command and translate its failures into HA errors."""
    try:
        return await command
    except SatelCommandRejectedError as err:
        key = _REJECTION_KEYS.get(err.result.code, "command_rejected")  # type: ignore[call-overload]
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={"code": f"0x{int(err.result.code):02X}"},
        ) from err
    except (SatelNotConnectedError, SatelCommandExpiredError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="not_connected"
        ) from err
    except SatelNoResponseError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="no_response"
        ) from err
    except ValueError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_command",
            translation_placeholders={"error": str(err)},
        ) from err
    except SatelIntegraError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="command_failed",
            translation_placeholders={"error": str(err)},
        ) from err
