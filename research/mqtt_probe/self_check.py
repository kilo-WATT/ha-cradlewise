"""Local safety self-checks for the dry-run probe."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from .auth_probe import _require_environment_credentials
from .provisioning_probe import (
    _build_live_provisioning_payload,
    _normalize_discovered_cradles,
    _response_structure,
    _safe_failure_report,
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
    validate_live_command_gates,
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


def _check_provisioning_response_structure() -> dict[str, str]:
    structure = _response_structure(
        {
            "deviceConfig": {
                "s3Bucket": "redacted",
                "s3ObjectKeys": ["redacted", "redacted"],
                "deviceId": "redacted",
                "cradleId": "redacted",
                "groupCaCert": "redacted",
                "roleId": "redacted",
                "babyId": "redacted",
            }
        }
    )
    expected = {
        "deviceConfig_present": True,
        "s3Bucket_present": True,
        "s3ObjectKeys_count": 2,
        "deviceId_present": True,
        "cradleId_present": True,
        "groupCaCert_present": True,
        "role_association_present": True,
        "baby_association_present": True,
    }
    if structure != expected:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "provisioning_response_structure"}


def _check_missing_baby_id_blocks() -> dict[str, str]:
    return _expect_safety_error(
        "missing_baby_id_for_provisioning",
        lambda: _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=[{"cradleId": "redacted"}],
        ),
    )


def _check_empty_cradles_block() -> dict[str, str]:
    return _expect_safety_error(
        "no_cradles_discovered",
        lambda: _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=[],
        ),
    )


def _check_dict_cradles_normalize() -> dict[str, str]:
    cradles = _normalize_discovered_cradles(
        {
            "redacted_key": {"babyId": "redacted"},
            "another_redacted_key": {"babyId": "redacted"},
        }
    )
    if len(cradles) != 2:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "dict_cradles_normalize"}


def _check_empty_dict_cradles_block() -> dict[str, str]:
    return _expect_safety_error(
        "no_cradles_discovered",
        lambda: _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=_normalize_discovered_cradles({}),
        ),
    )


def _check_unexpected_cradle_shape_does_not_crash() -> dict[str, str]:
    return _expect_safety_error(
        "missing_baby_id_for_provisioning",
        lambda: _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=_normalize_discovered_cradles(object()),
        ),
    )


def _check_failure_report_after_post_attempt() -> dict[str, str]:
    import research.mqtt_probe.provisioning_probe as provisioning_probe

    original_count = provisioning_probe._PROVISIONING_REQUESTS_THIS_RUN
    try:
        provisioning_probe._PROVISIONING_REQUESTS_THIS_RUN = 1
        report = _safe_failure_report("SomeError", "after_provisioning_request")
        if report["provisioning_request_attempted"] is not True:
            raise SafetyError("self_check_failed")
        if report["provisioning_request_count"] != 1:
            raise SafetyError("self_check_failed")
    finally:
        provisioning_probe._PROVISIONING_REQUESTS_THIS_RUN = original_count

    return {
        "result": "passed",
        "category": "failure_report_after_post_attempt",
    }


def _check_live_gate(
    category: str,
    *,
    command: str,
    allow_live_auth: bool = False,
    allow_live_provisioning: bool = False,
    acknowledge_provisioning_side_effect: bool = False,
) -> dict[str, str]:
    return _expect_safety_error(
        category,
        lambda: validate_live_command_gates(
            command=command,
            allow_live_auth=allow_live_auth,
            allow_live_provisioning=allow_live_provisioning,
            acknowledge_provisioning_side_effect=(
                acknowledge_provisioning_side_effect
            ),
        ),
    )


def run_self_checks() -> dict[str, Any]:
    """Run local checks without network, credentials, or generated files."""
    return {
        "mode": "dry_run",
        "network_attempted": False,
        "checks": [
            _check_redaction(),
            _check_provisioning_shape(),
            _check_provisioning_response_structure(),
            _check_desired_state_rejection(),
            _check_dict_cradles_normalize(),
            _check_empty_cradles_block(),
            _check_empty_dict_cradles_block(),
            _check_missing_baby_id_blocks(),
            _check_unexpected_cradle_shape_does_not_crash(),
            _check_failure_report_after_post_attempt(),
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
            _check_live_gate(
                "live_auth_explicit_flag_required",
                command="provisioning-inspect",
            ),
            _check_live_gate(
                "live_provisioning_explicit_flag_required",
                command="provisioning-inspect",
                allow_live_auth=True,
            ),
            _check_live_gate(
                "provisioning_side_effect_ack_required",
                command="provisioning-inspect",
                allow_live_auth=True,
                allow_live_provisioning=True,
            ),
            _expect_safety_error(
                "secret_cli_argument_rejected",
                lambda: reject_secret_arguments(
                    [
                        "provisioning-inspect",
                        "--allow-live-auth",
                        "--allow-live-provisioning",
                        "--acknowledge-provisioning-side-effect",
                        "--password=secret",
                    ]
                ),
            ),
            _expect_safety_error(
                "identifier_cli_argument_rejected",
                lambda: reject_secret_arguments(
                    [
                        "provisioning-inspect",
                        "--allow-live-auth",
                        "--allow-live-provisioning",
                        "--acknowledge-provisioning-side-effect",
                        "user@example.com",
                    ]
                ),
            ),
            _expect_safety_error(
                "certificate_download_disabled",
                certificate_download_disabled,
            ),
            _expect_safety_error("mqtt_connection_disabled", mqtt_connection_disabled),
            _expect_safety_error("mqtt_publish_disabled", mqtt_publish_disabled),
        ],
    }
