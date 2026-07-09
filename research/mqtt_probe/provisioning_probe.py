"""Dry-run provisioning preview without constructing a live request."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from .auth_probe import (
    _credential_environment,
    _require_environment_credentials,
    _with_timeout,
)
from .metadata import PROVISIONING_METHOD, PROVISIONING_PATH
from .redaction import REDACTED, normalized_error_category, redact
from .safety import SafetyError, assert_no_desired_state

_PROVISIONING_REQUESTS_THIS_RUN = 0

# Confirmed by offline DEX bytecode decoding of GetDeviceCertV3Request and
# DeviceInfoCert (see research/cradlewise-control-endpoints.md). Field order
# matches the recovered <init> constructor order.
_DEVICE_INFO_CERT_FIELDS = (
    "registrationDate",
    "appVersion",
    "country",
    "os",
    "deviceName",
    "osVersion",
    "timezone",
    "type",
    "resolution",
)


def build_provisioning_request_shape() -> dict[str, Any]:
    """Return the fully redacted request shape confirmed by static analysis.

    Field names and nesting match the decompiled `GetDeviceCertV3Request` and
    `DeviceInfoCert` models: `emailId`/`babyId`/`fcmToken`/`device`. Every
    value here is the fixed redaction marker, deliberately including
    `babyId` and `device.*`, so nothing resembling real request data ever
    appears in preview output. See `build_provisioning_request_field_types`
    for the confirmed JSON type of each field.
    """
    return {
        "emailId": REDACTED,
        "babyId": REDACTED,
        "fcmToken": REDACTED,
        "device": {field: REDACTED for field in _DEVICE_INFO_CERT_FIELDS},
    }


def validate_provisioning_request_shape(shape: dict[str, Any]) -> None:
    """Validate that the preview stays fully redacted and matches the confirmed model."""
    required = {"emailId", "babyId", "fcmToken", "device"}
    if set(shape) != required:
        raise SafetyError("unexpected_provisioning_shape")
    if shape["emailId"] != REDACTED:
        raise SafetyError("identifier_in_preview_rejected")
    if shape["babyId"] != REDACTED:
        raise SafetyError("identifier_in_preview_rejected")
    if shape["fcmToken"] is None:
        raise SafetyError("fcm_token_null_in_preview")
    if shape["fcmToken"] != REDACTED:
        raise SafetyError("identifier_in_preview_rejected")
    if not isinstance(shape["device"], dict) or set(shape["device"]) != set(
        _DEVICE_INFO_CERT_FIELDS
    ):
        raise SafetyError("invalid_device_shape")
    if any(value != REDACTED for value in shape["device"].values()):
        raise SafetyError("identifier_in_preview_rejected")
    assert_no_desired_state(shape)


def build_provisioning_request_field_types() -> dict[str, Any]:
    """Return confirmed field-type metadata for the provisioning request.

    This is descriptive metadata only, never a live or redacted value, so it
    is safe to show a real JSON type name. Keys are deliberately spelled
    `*_type`/`device_types` rather than the literal field names (`babyId`,
    `fcmToken`) so `redaction.redact`'s sensitive-key filter never matches
    them and silently overwrites this metadata with the generic redaction
    marker. `babyId` is confirmed to serialize as a JSON number: the app
    builds `java.math.BigDecimal(babyId)` before constructing the request.
    Every other field is a JSON string.
    """
    return {
        "emailId_type": "string",
        "babyId_type": "number/BigDecimal",
        "fcmToken_type": "string",
        "device_types": {field: "string" for field in _DEVICE_INFO_CERT_FIELDS},
    }


def validate_provisioning_request_field_types(field_types: dict[str, Any]) -> None:
    """Validate that field-type metadata matches the confirmed model."""
    required = {"emailId_type", "babyId_type", "fcmToken_type", "device_types"}
    if set(field_types) != required:
        raise SafetyError("unexpected_provisioning_field_types")
    if field_types["emailId_type"] != "string":
        raise SafetyError("unexpected_provisioning_field_types")
    if field_types["babyId_type"] != "number/BigDecimal":
        raise SafetyError("unexpected_baby_id_field_type")
    if field_types["fcmToken_type"] != "string":
        raise SafetyError("unexpected_provisioning_field_types")
    if not isinstance(field_types["device_types"], dict) or set(
        field_types["device_types"]
    ) != set(_DEVICE_INFO_CERT_FIELDS):
        raise SafetyError("invalid_device_field_types")
    if any(value != "string" for value in field_types["device_types"].values()):
        raise SafetyError("invalid_device_field_types")
    assert_no_desired_state(field_types)


def provisioning_preview() -> dict[str, Any]:
    """Return a fixed, fully redacted provisioning shape plus field-type metadata."""
    request_shape = build_provisioning_request_shape()
    validate_provisioning_request_shape(request_shape)

    request_field_types = build_provisioning_request_field_types()
    validate_provisioning_request_field_types(request_field_types)

    preview: dict[str, Any] = {
        "mode": "dry_run",
        "network_attempted": False,
        "request_attempted": False,
        "method": PROVISIONING_METHOD,
        "path": PROVISIONING_PATH,
        "request_shape": request_shape,
        "request_field_types": request_field_types,
        "expected_response_shape": {
            "deviceConfig_present": "boolean",
            "s3Bucket_present": "boolean",
            "s3ObjectKeys_count": "integer",
            "deviceId_present": "boolean",
            "cradleId_present": "boolean",
            "groupCaCert_present": "boolean",
            "role_association_present": "boolean",
            "baby_association_present": "boolean",
        },
        "result": "preview_only",
    }

    assert_no_desired_state(preview)
    return preview


def _empty_response_structure() -> dict[str, Any]:
    return {
        "deviceConfig_present": False,
        "s3Bucket_present": False,
        "s3ObjectKeys_count": 0,
        "deviceId_present": False,
        "cradleId_present": False,
        "groupCaCert_present": False,
        "role_association_present": False,
        "baby_association_present": False,
    }


def _http_status_class(status: int | None) -> str | None:
    if status is None:
        return None
    if 100 <= status <= 599:
        return f"{status // 100}xx"
    return None


def _http_status_metadata(error: BaseException | None) -> dict[str, Any]:
    """Extract only safe HTTP status metadata from response exceptions."""
    status: int | None = None
    if error is not None:
        raw_status = getattr(error, "status", None)
        if raw_status is None:
            response = getattr(error, "response", None)
            raw_status = getattr(response, "status_code", None)
        if isinstance(raw_status, int):
            status = raw_status

    return {
        "http_status": status,
        "http_status_class": _http_status_class(status),
    }


def _safe_failure_report(
    category: str,
    stage: str,
    *,
    app_config_present: bool = False,
    auth_success: bool = False,
    cradle_count: int | None = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    report = {
        "mode": "live_provisioning",
        "network_attempted": True,
        "method": PROVISIONING_METHOD,
        "path": PROVISIONING_PATH,
        "app_config_present": app_config_present,
        "auth_success": auth_success,
        "cradle_count": cradle_count,
        "provisioning_request_attempted": (
            stage == "provisioning_request" or _PROVISIONING_REQUESTS_THIS_RUN > 0
        ),
        "provisioning_request_count": _PROVISIONING_REQUESTS_THIS_RUN,
        "response_structure": _empty_response_structure(),
        "result": "failed",
        "failure_category": category,
        "failure_stage": stage,
        "credential_environment": _credential_environment(),
    }
    report.update(_http_status_metadata(error))
    return report


def _normalize_key(key: object) -> str:
    return "".join(character for character in str(key).lower() if character.isalnum())


def _object_to_safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    result: dict[str, Any] = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        try:
            item = getattr(value, name)
        except Exception:
            continue
        if callable(item):
            continue
        result[name] = item
    return result


def _mapping_get(mapping: dict[str, Any], *names: str) -> Any:
    normalized_names = {_normalize_key(name) for name in names}
    for key, value in mapping.items():
        if _normalize_key(key) in normalized_names:
            return value
    return None


def _present(mapping: dict[str, Any], *names: str) -> bool:
    value = _mapping_get(mapping, *names)
    if value is None:
        return False
    if isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    return True


def _response_structure(response: Any) -> dict[str, Any]:
    mapping = _object_to_safe_mapping(response)
    device_config = _mapping_get(mapping, "deviceConfig", "device_config")
    device_config_mapping = (
        _object_to_safe_mapping(device_config) if device_config is not None else {}
    )
    source = device_config_mapping or mapping

    object_keys = _mapping_get(
        source,
        "s3ObjectKeys",
        "s3_object_keys",
        "objectKeys",
        "object_keys",
    )
    if isinstance(object_keys, dict):
        object_key_count = len(object_keys)
    elif isinstance(object_keys, list):
        object_key_count = len(object_keys)
    elif object_keys is None:
        object_key_count = 0
    else:
        object_key_count = 1

    return {
        "deviceConfig_present": device_config is not None,
        "s3Bucket_present": _present(source, "s3Bucket", "s3_bucket"),
        "s3ObjectKeys_count": object_key_count,
        "deviceId_present": _present(source, "deviceId", "device_id"),
        "cradleId_present": _present(source, "cradleId", "cradle_id"),
        "groupCaCert_present": _present(source, "groupCaCert", "group_ca_cert"),
        "role_association_present": _present(
            source,
            "roleId",
            "role_id",
            "role",
            "roleAssociation",
            "role_association",
        ),
        "baby_association_present": _present(
            source,
            "babyId",
            "baby_id",
            "baby",
            "babyAssociation",
            "baby_association",
        ),
    }


def _extract_identifier(value: Any, *names: str) -> Any:
    mapping = _object_to_safe_mapping(value)
    return _mapping_get(mapping, *names)


def _normalize_discovered_cradles(value: Any) -> list[Any]:
    """Normalize discovered cradle containers without exposing keys."""
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    if value:
        return [value]
    return []


def _build_live_provisioning_payload(
    *,
    email: str,
    cradles: list[Any],
) -> dict[str, Any]:
    if not cradles:
        raise SafetyError("no_cradles_discovered")

    first_cradle = cradles[0]
    baby_id = _extract_identifier(first_cradle, "babyId", "baby_id")
    if baby_id is None:
        raise SafetyError("missing_baby_id_for_provisioning")
    if isinstance(baby_id, str) and not baby_id.strip():
        raise SafetyError("missing_baby_id_for_provisioning")

    payload = {
        "baby_id": baby_id,
        "email": email,
        "fcm_token": None,
        "device": {
            "app_version": "research-probe",
            "device_name": "research-probe",
            "os": "python",
            "os_version": "unknown",
        },
    }
    if payload["baby_id"] is None:
        raise SafetyError("missing_baby_id_for_provisioning")
    assert_no_desired_state(payload)
    return payload


def _api_request_body_kwargs(
    api_request: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        signature = inspect.signature(api_request)
    except (TypeError, ValueError) as error:
        raise SafetyError("pycradlewise_api_signature_unknown") from error

    parameters = signature.parameters
    for body_name in ("body", "json_body"):
        if body_name in parameters:
            return {body_name: payload}

    raise SafetyError("pycradlewise_api_signature_unknown")


async def _post_provisioning_once(client: Any, payload: dict[str, Any]) -> Any:
    global _PROVISIONING_REQUESTS_THIS_RUN
    if _PROVISIONING_REQUESTS_THIS_RUN >= 1:
        raise SafetyError("provisioning_request_limit_reached")

    api_request = getattr(client, "_api_request", None)
    if api_request is None or not callable(api_request):
        raise SafetyError("pycradlewise_api_request_unavailable")

    body_kwargs = _api_request_body_kwargs(api_request, payload)
    _PROVISIONING_REQUESTS_THIS_RUN += 1
    return await _with_timeout(
        api_request(
            PROVISIONING_METHOD,
            PROVISIONING_PATH,
            **body_kwargs,
        ),
        "provisioning_request",
    )


async def _live_provisioning_inspection_async() -> dict[str, Any]:
    email, password = _require_environment_credentials()

    try:
        from pycradlewise import (  # type: ignore[import-not-found]
            CradlewiseAuth,
            CradlewiseAuthError,
            CradlewiseClient,
            get_app_config,
        )
    except Exception:
        return _safe_failure_report("pycradlewise_unavailable", "import")

    app_config = None
    try:
        app_config = await _with_timeout(get_app_config(), "get_app_config")
    except SafetyError as error:
        if error.category == "timeout:get_app_config":
            return _safe_failure_report("TimeoutError", "get_app_config")
        raise
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "get_app_config",
            error=error,
        )

    auth = CradlewiseAuth(
        email=email,
        password=password,
        app_config=app_config,
    )
    client = CradlewiseClient(auth)

    try:
        await _with_timeout(auth.authenticate(), "authenticate")
    except SafetyError as error:
        if error.category == "timeout:authenticate":
            return _safe_failure_report(
                "TimeoutError",
                "authenticate",
                app_config_present=app_config is not None,
            )
        raise
    except CradlewiseAuthError:
        return _safe_failure_report(
            "invalid_auth",
            "authenticate",
            app_config_present=app_config is not None,
        )
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "authenticate",
            app_config_present=app_config is not None,
            error=error,
        )

    cradle_count: int | None = None
    try:
        cradles = await _with_timeout(
            client.discover_cradles(),
            "discover_cradles",
        )
    except SafetyError as error:
        if error.category == "timeout:discover_cradles":
            return _safe_failure_report(
                "TimeoutError",
                "discover_cradles",
                app_config_present=app_config is not None,
                auth_success=True,
            )
        raise
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "discover_cradles",
            app_config_present=app_config is not None,
            auth_success=True,
            error=error,
        )

    try:
        cradles = _normalize_discovered_cradles(cradles)
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "normalize_discovered_cradles",
            app_config_present=app_config is not None,
            auth_success=True,
            error=error,
        )

    cradle_count = len(cradles)

    try:
        payload = _build_live_provisioning_payload(email=email, cradles=cradles)
    except SafetyError as error:
        return _safe_failure_report(
            error.category,
            "build_provisioning_payload",
            app_config_present=app_config is not None,
            auth_success=True,
            cradle_count=cradle_count,
        )
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "build_provisioning_payload",
            app_config_present=app_config is not None,
            auth_success=True,
            cradle_count=cradle_count,
            error=error,
        )

    try:
        response = await _post_provisioning_once(client, payload)
    except SafetyError as error:
        if error.category == "timeout:provisioning_request":
            return _safe_failure_report(
                "TimeoutError",
                "provisioning_request",
                app_config_present=app_config is not None,
                auth_success=True,
                cradle_count=cradle_count,
            )
        return _safe_failure_report(
            error.category,
            "provisioning_request",
            app_config_present=app_config is not None,
            auth_success=True,
            cradle_count=cradle_count,
        )
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "provisioning_request",
            app_config_present=app_config is not None,
            auth_success=True,
            cradle_count=cradle_count,
            error=error,
        )

    result = {
        "mode": "live_provisioning",
        "network_attempted": True,
        "method": PROVISIONING_METHOD,
        "path": PROVISIONING_PATH,
        "app_config_present": app_config is not None,
        "auth_success": True,
        "cradle_count": cradle_count,
        "provisioning_request_attempted": True,
        "provisioning_request_count": _PROVISIONING_REQUESTS_THIS_RUN,
        "response_structure": _response_structure(response),
        "result": "success",
        "failure_category": None,
        "failure_stage": None,
        "http_status": None,
        "http_status_class": None,
        "credential_environment": _credential_environment(),
    }
    assert_no_desired_state(result)
    return redact(result)


def live_provisioning_inspection() -> dict[str, Any]:
    """Run explicitly approved provisioning-response inspection only."""
    try:
        return asyncio.run(_live_provisioning_inspection_async())
    except SafetyError as error:
        return redact(
            _safe_failure_report(
                error.category,
                "provisioning_inspection",
            )
        )
    except Exception as error:
        return redact(
            _safe_failure_report(
                normalized_error_category(error),
                "provisioning_inspection",
                error=error,
            )
        )
