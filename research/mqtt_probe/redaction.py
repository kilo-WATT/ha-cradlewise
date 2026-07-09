"""Recursive redaction helpers for research output."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "<redacted>"

_SENSITIVE_KEYS = {
    "accesskey",
    "accesskeyid",
    "authorization",
    "babyid",
    "certificate",
    "clientsecret",
    "cookie",
    "cradleid",
    "credential",
    "deviceid",
    "email",
    "emailid",
    "fcmtoken",
    "groupcacert",
    "identityid",
    "objectkey",
    "password",
    "privatekey",
    "roleid",
    "s3bucket",
    "secretaccesskey",
    "serial",
    "serialnumber",
    "sessiontoken",
    "signedurl",
    "token",
}

_EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"
)
_AWS_KEY_PATTERN = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_PEM_PATTERN = re.compile(
    r"-----BEGIN [^-]+-----.*?-----END [^-]+-----",
    re.DOTALL,
)
_QUERY_SECRET_PATTERN = re.compile(
    r"(?i)([?&](?:token|key|secret|signature|credential)=)[^&#\s]+"
)


def _normalize_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _is_sensitive_key(key: object) -> bool:
    normalized = _normalize_key(key)
    return any(
        normalized == sensitive or normalized.endswith(sensitive)
        for sensitive in _SENSITIVE_KEYS
    )


def redact_text(value: str) -> str:
    """Redact secret-like content embedded in text."""
    value = _PEM_PATTERN.sub(REDACTED, value)
    value = _EMAIL_PATTERN.sub(REDACTED, value)
    value = _AWS_KEY_PATTERN.sub(REDACTED, value)
    value = _BEARER_PATTERN.sub(REDACTED, value)
    value = _QUERY_SECRET_PATTERN.sub(r"\1<redacted>", value)
    return value


def redact(value: Any) -> Any:
    """Recursively redact mappings, sequences, and text."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = redact_text(str(key))
            result[safe_key] = REDACTED if _is_sensitive_key(key) else redact(item)
        return result

    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return [redact(item) for item in value]

    if isinstance(value, str):
        return redact_text(value)

    if isinstance(value, (bool, int, float)) or value is None:
        return value

    return f"<{type(value).__name__}>"


def normalized_error_category(error: BaseException) -> str:
    """Return an exception category without exposing its message."""
    name = type(error).__name__
    safe_name = re.sub(r"[^A-Za-z0-9_]", "", name)
    return safe_name or "UnknownError"
