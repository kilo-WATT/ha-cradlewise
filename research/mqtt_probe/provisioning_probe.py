"""Dry-run provisioning preview without constructing a live request."""

from __future__ import annotations

from typing import Any

from .metadata import PROVISIONING_METHOD, PROVISIONING_PATH
from .safety import assert_no_desired_state


def provisioning_preview() -> dict[str, Any]:
    """Return a fixed redacted provisioning shape."""
    preview: dict[str, Any] = {
        "mode": "dry_run",
        "network_attempted": False,
        "request_attempted": False,
        "method": PROVISIONING_METHOD,
        "path": PROVISIONING_PATH,
        "request_shape": {
            "baby_id": "<redacted>",
            "email": "<redacted>",
            "fcm_token": "<redacted-or-missing>",
            "device": {
                "app_version": "string",
                "device_name": "<generic>",
                "os": "string",
                "os_version": "string",
            },
        },
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
