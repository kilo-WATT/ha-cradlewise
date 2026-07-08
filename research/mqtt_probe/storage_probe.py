"""Disabled certificate-storage phase placeholder."""

from __future__ import annotations

from typing import NoReturn

from .safety import certificate_download_disabled


def download_certificate_material() -> NoReturn:
    """Reject certificate downloads until a later approved phase."""
    certificate_download_disabled()
