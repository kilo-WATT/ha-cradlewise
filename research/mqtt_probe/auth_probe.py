"""Dry-run authentication preflight without network access."""

from __future__ import annotations

import os
from typing import Any

from .metadata import AWS_REGION

_EMAIL_ENV = "CRADLEWISE_EMAIL"
_PASSWORD_ENV = "CRADLEWISE_PASSWORD"


def _environment_value_present(name: str) -> bool:
    """Return whether an environment value exists without returning its value."""
    value = os.environ.get(name)
    return value is not None and bool(value.strip())


def authentication_preview() -> dict[str, Any]:
    """Return safe authentication metadata without authenticating."""
    email_present = _environment_value_present(_EMAIL_ENV)
    password_present = _environment_value_present(_PASSWORD_ENV)

    return {
        "mode": "dry_run",
        "network_attempted": False,
        "authentication_attempted": False,
        "region": AWS_REGION,
        "credential_environment": {
            "email_present": email_present,
            "password_present": password_present,
            "complete": email_present and password_present,
        },
        "credential_expiration_present": False,
        "result": "preflight_only",
    }
