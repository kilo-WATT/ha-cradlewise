"""Local safety self-checks for the dry-run probe."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from .auth_probe import _require_environment_credentials
from .provisioning_probe import (
    _DEVICE_ENV_BY_FIELD,
    _DEVICE_INFO_CERT_FIELDS,
    _FCM_TOKEN_ENV,
    _baby_id_to_number,
    _build_live_provisioning_payload,
    _http_status_metadata,
    _normalize_discovered_cradles,
    _response_structure,
    _safe_failure_report,
    build_provisioning_request_field_types,
    build_provisioning_request_shape,
    validate_provisioning_request_field_types,
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


# Obviously fake, non-identifying placeholders. Used only to drive payload
# construction inside self-checks; their values are never printed.
_FAKE_PROVISIONING_ENV = {
    _FCM_TOKEN_ENV: "fake-fcm-token",
    "CRADLEWISE_DEVICE_REGISTRATION_DATE": "1970-01-01",
    "CRADLEWISE_DEVICE_APP_VERSION": "0.0.0",
    "CRADLEWISE_DEVICE_NAME": "fake-device",
    "CRADLEWISE_DEVICE_OS_VERSION": "0",
    "CRADLEWISE_DEVICE_TIMEZONE": "UTC",
    "CRADLEWISE_DEVICE_TYPE": "fake",
    "CRADLEWISE_DEVICE_RESOLUTION": "0x0",
}
_FAKE_NUMERIC_BABY_CRADLE = {"babyId": "12345"}


@contextmanager
def _temporary_environment(
    present: dict[str, str],
    absent: Iterable[str] = (),
) -> Iterator[None]:
    """Set/unset environment variables for a check, restoring them afterward."""
    names = set(present) | set(absent)
    saved: dict[str, str | None] = {name: os.environ.get(name) for name in names}
    try:
        for name, value in present.items():
            os.environ[name] = value
        for name in absent:
            os.environ.pop(name, None)
        yield
    finally:
        for name, original in saved.items():
            if original is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = original


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


def _check_email_id_key_redacts() -> dict[str, str]:
    # The value is deliberately NOT email-shaped, so this passes only if the
    # "emailId" key itself is treated as sensitive (not the value pattern).
    redacted = redact({"emailId": "not-email-shaped-identifier"})
    if redacted["emailId"] != REDACTED:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "email_id_key_redacts"}


def _check_provisioning_shape() -> dict[str, str]:
    shape = build_provisioning_request_shape()
    validate_provisioning_request_shape(shape)
    return {"result": "passed", "category": "provisioning_shape"}


def _check_provisioning_shape_field_names() -> dict[str, str]:
    shape = build_provisioning_request_shape()
    if set(shape) != {"emailId", "babyId", "fcmToken", "device"}:
        raise SafetyError("self_check_failed")
    if set(shape["device"]) != set(_DEVICE_INFO_CERT_FIELDS):
        raise SafetyError("self_check_failed")
    # Guard against regressing to the old, known-wrong snake_case shape.
    stale_keys = {"baby_id", "email", "fcm_token"}
    if stale_keys & set(shape):
        raise SafetyError("self_check_failed")
    stale_device_keys = {"app_version", "device_name", "os_version"}
    if stale_device_keys & set(shape["device"]):
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "provisioning_shape_field_names"}


def _check_provisioning_shape_fully_redacted() -> dict[str, str]:
    shape = build_provisioning_request_shape()
    if shape["emailId"] != REDACTED or shape["babyId"] != REDACTED:
        raise SafetyError("self_check_failed")
    if shape["fcmToken"] is None or shape["fcmToken"] != REDACTED:
        raise SafetyError("self_check_failed")
    if any(value != REDACTED for value in shape["device"].values()):
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "provisioning_shape_fully_redacted"}


def _check_provisioning_shape_idempotent_under_redaction() -> dict[str, str]:
    # Proves the preview shape is unchanged by the same redact() pass the
    # real CLI output goes through, i.e. it was already fully redacted.
    shape = build_provisioning_request_shape()
    if redact(shape) != shape:
        raise SafetyError("self_check_failed")
    return {
        "result": "passed",
        "category": "provisioning_shape_idempotent_under_redaction",
    }


def _check_provisioning_field_types() -> dict[str, str]:
    field_types = build_provisioning_request_field_types()
    validate_provisioning_request_field_types(field_types)
    stale_keys = {
        "emailId",
        "babyId",
        "fcmToken",
        "device",
        "baby_id",
        "email",
        "fcm_token",
    }
    if stale_keys & set(field_types):
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "provisioning_field_types"}


def _check_provisioning_field_types_survive_redaction() -> dict[str, str]:
    # Proves the babyId type note is not caught by the sensitive-key filter
    # and silently overwritten with the generic redaction marker.
    field_types = build_provisioning_request_field_types()
    redacted_field_types = redact(field_types)
    if redacted_field_types != field_types:
        raise SafetyError("self_check_failed")
    if redacted_field_types["babyId_type"] != "number/BigDecimal":
        raise SafetyError("self_check_failed")
    return {
        "result": "passed",
        "category": "provisioning_field_types_survive_redaction",
    }


def _check_real_numeric_baby_id_redacts_to_string() -> dict[str, str]:
    # Proves a real numeric babyId occurring anywhere under the sensitive
    # "babyId" key still redacts to the generic string marker, never a
    # number. This guards against ever reintroducing a type-preserving
    # redaction path for sensitive keys.
    redacted = redact({"babyId": 123456789})
    if redacted["babyId"] != REDACTED or not isinstance(redacted["babyId"], str):
        raise SafetyError("self_check_failed")
    return {
        "result": "passed",
        "category": "real_numeric_baby_id_redacts_to_string",
    }


def _check_baby_id_numeric_conversion() -> dict[str, str]:
    # Integer-like strings and native numbers convert to JSON numbers;
    # non-numeric and boolean values are rejected.
    if _baby_id_to_number("12345") != 12345:
        raise SafetyError("self_check_failed")
    if not isinstance(_baby_id_to_number("12345"), int):
        raise SafetyError("self_check_failed")
    if _baby_id_to_number(6789) != 6789:
        raise SafetyError("self_check_failed")
    if _baby_id_to_number("12.5") != 12.5:
        raise SafetyError("self_check_failed")
    _expect_safety_error(
        "baby_id_not_numeric_for_provisioning",
        lambda: _baby_id_to_number("not-a-number"),
    )
    _expect_safety_error(
        "baby_id_not_numeric_for_provisioning",
        lambda: _baby_id_to_number(True),
    )
    return {"result": "passed", "category": "baby_id_numeric_conversion"}


def _check_live_payload_shape() -> dict[str, str]:
    with _temporary_environment(_FAKE_PROVISIONING_ENV):
        payload = _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=[dict(_FAKE_NUMERIC_BABY_CRADLE)],
        )
    if set(payload) != {"emailId", "babyId", "fcmToken", "device"}:
        raise SafetyError("self_check_failed")
    # Guard against regressing to the old, known-wrong snake_case shape.
    if {"baby_id", "email", "fcm_token"} & set(payload):
        raise SafetyError("self_check_failed")
    if isinstance(payload["babyId"], bool) or not isinstance(
        payload["babyId"], (int, float)
    ):
        raise SafetyError("self_check_failed")
    if not isinstance(payload["fcmToken"], str) or not payload["fcmToken"]:
        raise SafetyError("self_check_failed")
    device = payload["device"]
    if set(device) != set(_DEVICE_INFO_CERT_FIELDS):
        raise SafetyError("self_check_failed")
    if device["country"] != "IN" or device["os"] != "android":
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "live_payload_shape"}


def _check_live_payload_baby_id_numeric() -> dict[str, str]:
    with _temporary_environment(_FAKE_PROVISIONING_ENV):
        payload = _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=[{"babyId": "987654321"}],
        )
    if payload["babyId"] != 987654321:
        raise SafetyError("self_check_failed")
    if isinstance(payload["babyId"], bool) or not isinstance(payload["babyId"], int):
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "live_payload_baby_id_numeric"}


def _check_missing_fcm_token_blocks_before_post() -> dict[str, str]:
    # Device info present, fcm token absent: must block before any POST.
    device_only = {
        name: value
        for name, value in _FAKE_PROVISIONING_ENV.items()
        if name != _FCM_TOKEN_ENV
    }
    with _temporary_environment(device_only, absent=(_FCM_TOKEN_ENV,)):
        return _expect_safety_error(
            "missing_fcm_token_for_provisioning",
            lambda: _build_live_provisioning_payload(
                email="redacted@example.invalid",
                cradles=[dict(_FAKE_NUMERIC_BABY_CRADLE)],
            ),
        )


def _check_missing_device_info_blocks_before_post() -> dict[str, str]:
    # fcm token present, one device env var absent: must block before POST.
    absent_field_env = _DEVICE_ENV_BY_FIELD["resolution"]
    present = {
        name: value
        for name, value in _FAKE_PROVISIONING_ENV.items()
        if name != absent_field_env
    }
    with _temporary_environment(present, absent=(absent_field_env,)):
        return _expect_safety_error(
            "missing_device_info_for_provisioning",
            lambda: _build_live_provisioning_payload(
                email="redacted@example.invalid",
                cradles=[dict(_FAKE_NUMERIC_BABY_CRADLE)],
            ),
        )


def _check_live_payload_redacts_identifiers() -> dict[str, str]:
    # The built payload is never emitted, but confirm that if it were passed
    # through redact() the email, babyId, and fcmToken would all be hidden.
    with _temporary_environment(_FAKE_PROVISIONING_ENV):
        payload = _build_live_provisioning_payload(
            email="redacted@example.invalid",
            cradles=[dict(_FAKE_NUMERIC_BABY_CRADLE)],
        )
    redacted = redact(payload)
    if redacted["emailId"] != REDACTED:
        raise SafetyError("self_check_failed")
    if redacted["babyId"] != REDACTED or not isinstance(redacted["babyId"], str):
        raise SafetyError("self_check_failed")
    if redacted["fcmToken"] != REDACTED:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "live_payload_redacts_identifiers"}


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


class _FakeHttpError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__("do not expose this message")
        self.status = status
        self.message = "do not expose this message"
        self.request_info = "https://example.invalid/secret"
        self.headers = {"authorization": "Bearer secret"}
        self.body = "secret response body"
        self.text = "secret response text"


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeResponseHttpError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__("do not expose response exception")
        self.response = _FakeResponse(status_code)
        self.url = "https://example.invalid/secret"
        self.cookies = {"session": "secret"}


def _assert_no_http_sensitive_values(report: dict[str, Any]) -> None:
    serialized = repr(report)
    forbidden = (
        "do not expose",
        "example.invalid",
        "authorization",
        "Bearer",
        "secret response",
        "session",
        "cookies",
        "headers",
        "body",
        "text",
        "url",
        "request_info",
    )
    if any(value in serialized for value in forbidden):
        raise SafetyError("self_check_failed")


def _check_http_status_metadata(status: int, status_class: str) -> dict[str, str]:
    error = _FakeHttpError(status)
    metadata = _http_status_metadata(error)
    if metadata != {"http_status": status, "http_status_class": status_class}:
        raise SafetyError("self_check_failed")

    report = _safe_failure_report(
        "ClientResponseError",
        "provisioning_request",
        error=error,
    )
    if report["http_status"] != status:
        raise SafetyError("self_check_failed")
    if report["http_status_class"] != status_class:
        raise SafetyError("self_check_failed")
    _assert_no_http_sensitive_values(report)
    return {"result": "passed", "category": f"http_status_{status}"}


def _check_response_status_metadata() -> dict[str, str]:
    metadata = _http_status_metadata(_FakeResponseHttpError(403))
    if metadata != {"http_status": 403, "http_status_class": "4xx"}:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "response_http_status_403"}


def _check_unknown_http_status_metadata() -> dict[str, str]:
    metadata = _http_status_metadata(Exception("do not expose"))
    if metadata != {"http_status": None, "http_status_class": None}:
        raise SafetyError("self_check_failed")
    return {"result": "passed", "category": "unknown_http_status"}


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
            _check_email_id_key_redacts(),
            _check_provisioning_shape(),
            _check_provisioning_shape_field_names(),
            _check_provisioning_shape_fully_redacted(),
            _check_provisioning_shape_idempotent_under_redaction(),
            _check_provisioning_field_types(),
            _check_provisioning_field_types_survive_redaction(),
            _check_real_numeric_baby_id_redacts_to_string(),
            _check_baby_id_numeric_conversion(),
            _check_live_payload_shape(),
            _check_live_payload_baby_id_numeric(),
            _check_missing_fcm_token_blocks_before_post(),
            _check_missing_device_info_blocks_before_post(),
            _check_live_payload_redacts_identifiers(),
            _check_provisioning_response_structure(),
            _check_desired_state_rejection(),
            _check_dict_cradles_normalize(),
            _check_empty_cradles_block(),
            _check_empty_dict_cradles_block(),
            _check_missing_baby_id_blocks(),
            _check_unexpected_cradle_shape_does_not_crash(),
            _check_failure_report_after_post_attempt(),
            _check_http_status_metadata(400, "4xx"),
            _check_http_status_metadata(403, "4xx"),
            _check_http_status_metadata(500, "5xx"),
            _check_response_status_metadata(),
            _check_unknown_http_status_metadata(),
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
