"""Dry-run provisioning preview without constructing a live request."""

from __future__ import annotations

from typing import Any

from .metadata import PROVISIONING_METHOD, PROVISIONING_PATH
from .safety import SafetyError, assert_no_desired_state


def build_provisioning_request_shape() -> dict[str, Any]:
    """Return the redacted request shape expected by the provisioning endpoint."""
    return {
        "baby_id": "<redacted>",
        "email": "<redacted>",
        "fcm_token": "<redacted-or-missing>",
        "device": {
            "app_version": "string",
            "device_name": "<generic>",
            "os": "string",
            "os_version": "string",
        },
    }


def validate_provisioning_request_shape(shape: dict[str, Any]) -> None:
    """Validate that the preview remains redacted and non-control-only."""
    required = {"baby_id", "email", "fcm_token", "device"}
    if set(shape) != required:
        raise SafetyError("unexpected_provisioning_shape")
    if shape["baby_id"] != "<redacted>" or shape["email"] != "<redacted>":
        raise SafetyError("identifier_in_preview_rejected")
    if not isinstance(shape["device"], dict):
        raise SafetyError("invalid_device_shape")
    assert_no_desired_state(shape)


def provisioning_preview() -> dict[str, Any]:
    """Return a fixed redacted provisioning shape."""
    request_shape = build_provisioning_request_shape()
    validate_provisioning_request_shape(request_shape)

    preview: dict[str, Any] = {
        "mode": "dry_run",
        "network_attempted": False,
        "request_attempted": False,
        "method": PROVISIONING_METHOD,
        "path": PROVISIONING_PATH,
        "request_shape": request_shape,
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
