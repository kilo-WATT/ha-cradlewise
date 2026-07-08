"""Diagnostics support for Cradlewise."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.core import HomeAssistant

from . import CradlewiseConfigEntry
from .const import CONF_EMAIL, CONF_PASSWORD

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "access_key",
    "access_token",
    "authorization",
    "certificate",
    "client_secret",
    "private_key",
    "refresh_token",
    "secret_key",
    "session_token",
    "token",
    "unique_id",
}

REST_STATE_FIELDS = {
    "actuator",
    "ambientTempInCelsius",
    "baby_present",
    "babyPresent",
    "baby_sleep_state",
    "babySleepPhase",
    "babySleepPhaseV2",
    "babySleepState",
    "bounceLevel",
    "isCribHelping",
    "keepBounceOnDuringSleep",
    "keepBounceOnDuringSleepLevel",
    "keepMusicOnDuringSleep",
    "keepMusicOnDuringSleepLevel",
    "light",
    "music",
    "musicLevel",
    "soundSynth",
    "startRecipeOn",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CradlewiseConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "poll_interval_seconds": int(coordinator.update_interval.total_seconds()),
        "cradles": [
            {
                "cradle_id": REDACTED,
                "baby_id": REDACTED if cradle.baby_id else None,
                "baby_name": REDACTED if cradle.baby_name else None,
                "serial_number": REDACTED if cradle.serial_number else None,
                "timezone": cradle.timezone,
                "online": cradle.online,
                "firmware_version": cradle.firmware_version,
                "day_start_time": cradle.day_start_time,
                "rest_state": {
                    key: value
                    for key, value in cradle.state.items()
                    if key in REST_STATE_FIELDS
                },
            }
            for cradle in coordinator.cradles.values()
        ],
        "analytics": [
            async_redact_data(asdict(analytics), TO_REDACT)
            for analytics in coordinator.analytics.values()
        ],
    }

