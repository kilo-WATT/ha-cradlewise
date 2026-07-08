"""Mandatory safety controls for the research scaffold."""

from __future__ import annotations

import socket
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

_SECRET_ARGUMENT_NAMES = {
    "--access-key",
    "--authorization",
    "--certificate",
    "--client-secret",
    "--cradle-id",
    "--device-id",
    "--email",
    "--fcm-token",
    "--password",
    "--private-key",
    "--secret-key",
    "--session-token",
    "--token",
}


class SafetyError(RuntimeError):
    """A normalized safety failure without sensitive details."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def assert_dry_run(enabled: bool) -> None:
    """Require dry-run mode."""
    if not enabled:
        raise SafetyError("dry_run_required")


def reject_secret_arguments(arguments: Sequence[str]) -> None:
    """Reject credentials and identifiers supplied through command arguments."""
    for argument in arguments:
        name = argument.split("=", 1)[0].lower()
        if name in _SECRET_ARGUMENT_NAMES:
            raise SafetyError("secret_cli_argument_rejected")


def _network_blocked(*args: object, **kwargs: object) -> NoReturn:
    del args, kwargs
    raise SafetyError("network_access_blocked")


def install_network_guard() -> None:
    """Block socket creation and outbound connections for this process."""
    socket.socket = _network_blocked  # type: ignore[assignment]
    socket.create_connection = _network_blocked  # type: ignore[assignment]


def assert_no_desired_state(value: Any) -> None:
    """Reject any object containing an MQTT desired-state field."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() == "desired":
                raise SafetyError("desired_state_rejected")
            assert_no_desired_state(item)
        return

    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for item in value:
            assert_no_desired_state(item)


def certificate_download_disabled() -> NoReturn:
    """Reject certificate download in the scaffold."""
    raise SafetyError("certificate_download_disabled")


def mqtt_connection_disabled() -> NoReturn:
    """Reject MQTT connections in the scaffold."""
    raise SafetyError("mqtt_connection_disabled")


def mqtt_publish_disabled() -> NoReturn:
    """Reject every MQTT publish operation."""
    raise SafetyError("mqtt_publish_disabled")
