"""Local safety self-checks for the dry-run probe."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from .auth_probe import _require_environment_credentials
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


@contextmanager
def _without_cradlewise_credentials() -> Iterator[None]:
    original_email = os.environ.pop("CRADLEWISE_EMAIL", None)
    original_password = os.environ.pop("CRADLEWISE_PASSWORD", None)
    try:
        yield
    finally:
        if original_email is not None:
            os.environ["CRADLEWISE_EMAIL"] = original_email
        else:
            os.environ.pop("CRADLEWISE_EMAIL", None)

        if original_password is not None:
            os.environ["CRADLEWISE_PASSWORD"] = original_password
        else:
            os.environ.pop("CRADLEWISE_PASSWORD", None)


def _check_missing_live_auth_credentials() -> dict[str, str]:
    with _without_cradlewise_credentials():
        return _expect_safety_error(
            "missing_live_auth_credentials",
            _require_environment_credentials,
        )


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
                "secret_cli_argument_rejected",
                lambda: reject_secret_arguments(
                    ["--allow-live-auth", "--email=user@example.com"]
                ),
            ),
            _expect_safety_error(
                "identifier_cli_argument_rejected",
                lambda: reject_secret_arguments(
                    ["--allow-live-auth", "user@example.com"]
                ),
            ),
            _check_missing_live_auth_credentials(),
            _expect_safety_error(
                "certificate_download_disabled",
                certificate_download_disabled,
            ),
            _expect_safety_error("mqtt_connection_disabled", mqtt_connection_disabled),
            _expect_safety_error("mqtt_publish_disabled", mqtt_publish_disabled),
        ],
    }
