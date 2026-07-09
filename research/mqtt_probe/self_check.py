"""Local safety self-checks for the dry-run probe."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .provisioning_probe import (
    build_provisioning_request_shape,
    validate_provisioning_request_shape,
)
from .redaction import REDACTED, redact
from .safety import (
    SafetyError,
    assert_no_desired_state,
    certificate_download_disabled,
    mqtt_connection_disabled,
    mqtt_publish_disabled,
    reject_secret_arguments,
)


def _expect_safety_error(
    category: str,
    callback: Callable[[], object],
) -> dict[str, str]:
    try:
        callback()
    except SafetyError as error:
        if error.category != category:
            raise SafetyError("self_check_failed") from error
        return {"result": "passed", "category": category}

    raise SafetyError("self_check_failed")


def _check_redaction() -> dict[str, str]:
    redacted = redact(
        {
            "email": "person@example.com",
            "deviceId": "device-identifier",
            "nested": ["Bearer abc.def.ghi"],
        }
    )
    if redacted["email"] != REDACTED:
        raise SafetyError("self_check_failed")
    if redacted["deviceId"] != REDACTED:
        raise SafetyError("self_check_failed")
    if redacted["nested"][0] != REDACTED:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "redaction"}


def _check_provisioning_shape() -> dict[str, str]:
    shape = build_provisioning_request_shape()
    validate_provisioning_request_shape(shape)
    return {"result": "passed", "category": "provisioning_shape"}


def _check_desired_state_rejection() -> dict[str, str]:
    return _expect_safety_error(
        "desired_state_rejected",
        lambda: assert_no_desired_state({"state": {"desired": {"x": True}}}),
    )


def run_self_checks() -> dict[str, Any]:
    """Run local checks without network, credentials, or generated files."""
    return {
        "mode": "dry_run",
        "network_attempted": False,
        "checks": [
            _check_redaction(),
            _check_provisioning_shape(),
            _check_desired_state_rejection(),
            _expect_safety_error(
                "identifier_cli_argument_rejected",
                lambda: reject_secret_arguments(["person@example.com"]),
            ),
            _expect_safety_error(
                "secret_cli_argument_rejected",
                lambda: reject_secret_arguments(["--password=secret"]),
            ),
            _expect_safety_error(
                "certificate_download_disabled",
                certificate_download_disabled,
            ),
            _expect_safety_error("mqtt_connection_disabled", mqtt_connection_disabled),
            _expect_safety_error("mqtt_publish_disabled", mqtt_publish_disabled),
        ],
    }
