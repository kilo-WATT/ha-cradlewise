"""Sensor entities for Cradlewise."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pycradlewise import CradlewiseCradle, SleepAnalytics

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
try:
    from homeassistant.const import EntityCategory
except ImportError:
    from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import CradlewiseCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse a datetime string from the API."""
    if not dt_str:
        return None
    
    dt_str = dt_str.strip()
    
    # Try ISO format first
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    # Try human-readable time (e.g. 1:05 pm)
    try:
        time_part = datetime.strptime(dt_str.lower(), "%I:%M %p").time()
        now = dt_util.now()
        return datetime.combine(now.date(), time_part, now.tzinfo)
    except ValueError:
        _LOGGER.debug("Failed to parse datetime string: %s", dt_str)
        return None


@dataclass(frozen=True, kw_only=True)
class CradlewiseSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[CradlewiseCradle], Any]
    icon_fn: Callable[[Any], str | None] | None = None


@dataclass(frozen=True, kw_only=True)
class CradlewiseAnalyticsEntityDescription(SensorEntityDescription):
    value_fn: Callable[[SleepAnalytics], Any]


SENSOR_DESCRIPTIONS: tuple[CradlewiseSensorEntityDescription, ...] = (
    CradlewiseSensorEntityDescription(
        key="sleep_stage",
        translation_key="sleep_stage",
        icon="mdi:sleep",
        value_fn=lambda c: c.sleep_stage_name,
    ),
    CradlewiseSensorEntityDescription(
        key="sleep_phase",
        translation_key="sleep_phase",
        icon="mdi:moon-waning-crescent",
        value_fn=lambda c: c.sleep_phase_name,
    ),
    CradlewiseSensorEntityDescription(
        key="bounce_amplitude",
        translation_key="bounce_amplitude",
        icon="mdi:sine-wave",
        value_fn=lambda c: c.bounce_amplitude,
    ),
    CradlewiseSensorEntityDescription(
        key="music_volume",
        translation_key="music_volume",
        icon="mdi:volume-medium",
        value_fn=lambda c: c.music_volume,
    ),
    CradlewiseSensorEntityDescription(
        key="music_track",
        translation_key="music_track",
        icon="mdi:music-box",
        value_fn=lambda c: c.music_track,
    ),
    CradlewiseSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        icon="mdi:thermometer",
        device_class="temperature",
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.temperature,
    ),
    CradlewiseSensorEntityDescription(
        key="day_start_time",
        translation_key="day_start_time",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.day_start_time,
    ),
    CradlewiseSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.firmware_version,
    ),
)

ANALYTICS_DESCRIPTIONS: tuple[CradlewiseAnalyticsEntityDescription, ...] = (
    CradlewiseAnalyticsEntityDescription(
        key="total_soothe_count",
        translation_key="soothe_count",
        icon="mdi:hand-heart",
        value_fn=lambda a: a.total_soothe_count,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="sleep_saved",
        translation_key="sleep_saved",
        icon="mdi:sleep",
        value_fn=lambda a: a.sleep_saved,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="nap_count",
        translation_key="nap_count",
        icon="mdi:counter",
        value_fn=lambda a: a.nap_count,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="rise_time_analytics",
        translation_key="rise_time",
        icon="mdi:weather-sunset-up",
        value_fn=lambda a: a.rise_time,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="bed_time",
        translation_key="bed_time",
        icon="mdi:weather-sunset-down",
        value_fn=lambda a: a.bed_time,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="time_in_bed",
        translation_key="time_in_bed",
        icon="mdi:bed-clock",
        value_fn=lambda a: a.time_in_bed,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="longest_stretch",
        translation_key="longest_stretch",
        icon="mdi:trophy",
        value_fn=lambda a: a.longest_stretch,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="awake_in_bed",
        translation_key="awake_in_bed",
        icon="mdi:eye",
        value_fn=lambda a: a.awake_in_bed,
    ),
    # Weekly Aggregates
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_sleep",
        translation_key="weekly_avg_sleep",
        icon="mdi:sleep",
        value_fn=lambda a: a.weekly_avg_sleep,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_day_sleep",
        translation_key="weekly_avg_day_sleep",
        icon="mdi:weather-sunny",
        value_fn=lambda a: a.weekly_avg_day_sleep,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_night_sleep",
        translation_key="weekly_avg_night_sleep",
        icon="mdi:weather-night",
        value_fn=lambda a: a.weekly_avg_night_sleep,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_nap_duration",
        translation_key="weekly_avg_nap_duration",
        icon="mdi:clock-outline",
        value_fn=lambda a: a.weekly_avg_nap_duration,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_naps_per_day",
        translation_key="weekly_avg_naps_per_day",
        icon="mdi:counter",
        value_fn=lambda a: f"{a.weekly_avg_naps_per_day:.1f}" if a.weekly_avg_naps_per_day is not None else None,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_rise_time",
        translation_key="weekly_avg_rise_time",
        icon="mdi:weather-sunset-up",
        value_fn=lambda a: a.weekly_avg_rise_time,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_bed_time",
        translation_key="weekly_avg_bed_time",
        icon="mdi:weather-sunset-down",
        value_fn=lambda a: a.weekly_avg_bed_time,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="weekly_avg_longest_stretch",
        translation_key="weekly_avg_longest_stretch",
        icon="mdi:trophy-outline",
        value_fn=lambda a: a.weekly_avg_longest_stretch,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="baby_age_text",
        translation_key="baby_age_text",
        icon="mdi:baby-face-outline",
        value_fn=lambda a: a.baby_age_text,
    ),
    CradlewiseAnalyticsEntityDescription(
        key="last_nap_start",
        translation_key="last_nap_start",
        icon="mdi:clock-start",
        device_class="timestamp",
        value_fn=lambda a: _parse_datetime(a.last_nap_start),
    ),
    CradlewiseAnalyticsEntityDescription(
        key="last_nap_end",
        translation_key="last_nap_end",
        icon="mdi:clock-end",
        device_class="timestamp",
        value_fn=lambda a: _parse_datetime(a.last_nap_end),
    ),
    CradlewiseAnalyticsEntityDescription(
        key="last_event",
        translation_key="last_event",
        icon="mdi:calendar-clock",
        value_fn=lambda a: a.last_event_value,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cradlewise sensors."""
    coordinator: CradlewiseCoordinator = entry.runtime_data

    entities: list[SensorEntity] = []
    for cradle in coordinator.cradles.values():
        for desc in SENSOR_DESCRIPTIONS:
            entities.append(CradlewiseSensor(coordinator, cradle, desc))
        for desc in ANALYTICS_DESCRIPTIONS:
            entities.append(CradlewiseAnalyticsSensor(coordinator, cradle, desc))

    async_add_entities(entities)


def _device_info(cradle: CradlewiseCradle) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, cradle.cradle_id)},
        "name": f"Cradlewise {cradle.baby_name or 'Crib'}",
        "manufacturer": "Cradlewise",
        "model": "Smart Crib",
        "sw_version": cradle.firmware_version,
    }


class CradlewiseSensor(CoordinatorEntity[CradlewiseCoordinator], SensorEntity):
    entity_description: CradlewiseSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CradlewiseCoordinator,
        cradle: CradlewiseCradle,
        description: CradlewiseSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._cradle_id = cradle.cradle_id
        self._attr_unique_id = f"{cradle.cradle_id}_{description.key}"
        self._attr_entity_category = description.entity_category
        self._attr_device_info = _device_info(cradle)

    @property
    def native_value(self) -> Any:
        cradle = self.coordinator.cradles.get(self._cradle_id)
        if cradle is None:
            return None
        return self.entity_description.value_fn(cradle)

    @property
    def icon(self) -> str | None:
        """Return the icon of the sensor."""
        if self.entity_description.icon_fn:
            return self.entity_description.icon_fn(self.native_value)
        return super().icon

    @property
    def available(self) -> bool:
        return self.coordinator.cradles.get(self._cradle_id) is not None and super().available


class CradlewiseAnalyticsSensor(CoordinatorEntity[CradlewiseCoordinator], SensorEntity):
    entity_description: CradlewiseAnalyticsEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CradlewiseCoordinator,
        cradle: CradlewiseCradle,
        description: CradlewiseAnalyticsEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._cradle_id = cradle.cradle_id
        self._baby_id = cradle.baby_id
        self._attr_unique_id = f"{cradle.cradle_id}_{description.key}"
        self._attr_entity_category = description.entity_category
        self._attr_device_info = _device_info(cradle)

    @property
    def native_value(self) -> Any:
        if not self._baby_id:
            return None
        analytics = self.coordinator.analytics.get(self._baby_id)
        if analytics is None:
            return None
        return self.entity_description.value_fn(analytics)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "last_event" or not self._baby_id:
            return None
        analytics = self.coordinator.analytics.get(self._baby_id)
        if analytics and analytics.last_event_time:
            return {"event_time": analytics.last_event_time}
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.cradles.get(self._cradle_id) is not None and super().available
