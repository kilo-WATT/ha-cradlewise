"""Authentication previews and explicitly gated live-auth probing."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .metadata import AWS_REGION
from .redaction import normalized_error_category, redact
from .safety import SafetyError

_EMAIL_ENV = "CRADLEWISE_EMAIL"
_PASSWORD_ENV = "CRADLEWISE_PASSWORD"

LIVE_AUTH_TIMEOUT_SECONDS = 20


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


def _credential_environment() -> dict[str, bool]:
    email_present = _environment_value_present(_EMAIL_ENV)
    password_present = _environment_value_present(_PASSWORD_ENV)
    return {
        "email_present": email_present,
        "password_present": password_present,
        "complete": email_present and password_present,
    }


def _require_environment_credentials() -> tuple[str, str]:
    email = os.environ.get(_EMAIL_ENV)
    password = os.environ.get(_PASSWORD_ENV)
    if email is None or not email.strip():
        raise SafetyError("missing_live_auth_credentials")
    if password is None or not password.strip():
        raise SafetyError("missing_live_auth_credentials")
    return email, password


def _credential_expiration_present(auth: object) -> bool:
    credentials = getattr(auth, "credentials", None)
    if credentials is None:
        return False
    return any(
        getattr(credentials, attribute, None) is not None
        for attribute in (
            "expiration",
            "expiration_time",
            "expires_at",
            "expiry_time",
        )
    )


def _safe_failure_report(
    category: str,
    stage: str,
    *,
    app_config_present: bool = False,
    authentication_attempted: bool = False,
) -> dict[str, Any]:
    return {
        "mode": "live_auth",
        "network_attempted": True,
        "authentication_attempted": authentication_attempted,
        "region": AWS_REGION,
        "credential_environment": _credential_environment(),
        "app_config_present": app_config_present,
        "credential_expiration_present": False,
        "cradle_count": None,
        "result": "failed",
        "failure_category": category,
        "failure_stage": stage,
    }


async def _with_timeout(awaitable: Any, stage: str) -> Any:
    try:
        return await asyncio.wait_for(
            awaitable,
            timeout=LIVE_AUTH_TIMEOUT_SECONDS,
        )
    except TimeoutError as error:
        raise SafetyError(f"timeout:{stage}") from error


async def _live_authentication_probe_async() -> dict[str, Any]:
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
                authentication_attempted=True,
            )
        raise
    except CradlewiseAuthError:
        return _safe_failure_report(
            "invalid_auth",
            "authenticate",
            app_config_present=app_config is not None,
            authentication_attempted=True,
        )
    except Exception as error:
        return _safe_failure_report(
            normalized_error_category(error),
            "authenticate",
            app_config_present=app_config is not None,
            authentication_attempted=True,
        )

    cradle_count: int | None = None
    discover_category: str | None = None
    try:
        cradles = await _with_timeout(
            client.discover_cradles(),
            "discover_cradles",
        )
        cradle_count = len(cradles)
    except SafetyError as error:
        if error.category == "timeout:discover_cradles":
            discover_category = "TimeoutError"
        else:
            raise
    except Exception as error:
        discover_category = normalized_error_category(error)

    result = {
        "mode": "live_auth",
        "network_attempted": True,
        "authentication_attempted": True,
        "region": AWS_REGION,
        "credential_environment": _credential_environment(),
        "app_config_present": app_config is not None,
        "credential_expiration_present": _credential_expiration_present(auth),
        "cradle_count": cradle_count,
        "result": "success" if discover_category is None else "partial_success",
        "discovery_failure_category": discover_category,
    }
    return redact(result)


def live_authentication_probe() -> dict[str, Any]:
    """Run explicitly approved live authentication without exposing secrets."""
    return asyncio.run(_live_authentication_probe_async())
