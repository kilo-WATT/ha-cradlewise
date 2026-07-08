"""DataUpdateCoordinator for Cradlewise."""

from __future__ import annotations

import logging
from datetime import timedelta

from pycradlewise import (
    AppConfig,
    CradlewiseApiError,
    CradlewiseClient,
    CradlewiseCradle,
    SleepAnalytics,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CradlewiseCoordinator(DataUpdateCoordinator[dict[str, CradlewiseCradle]]):
    """Coordinator to manage fetching Cradlewise data."""

    def __init__(
        self, hass: HomeAssistant, client: CradlewiseClient, app_config: AppConfig
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._app_config = app_config
        self.cradles: dict[str, CradlewiseCradle] = {}
        self.analytics: dict[str, SleepAnalytics] = {}

    async def _async_setup(self) -> None:
        try:
            self.cradles = await self.client.discover_cradles()
        except CradlewiseApiError as err:
            raise UpdateFailed(f"Failed to discover cradles: {err}") from err

    async def _async_update_data(self) -> dict[str, CradlewiseCradle]:
        if not self.cradles:
            await self._async_setup()

        for cradle in self.cradles.values():
            try:
                await self.client.update_cradle(cradle)
            except CradlewiseApiError as err:
                _LOGGER.warning("Failed to update %s: %s", cradle.cradle_id, err)

        for cradle in self.cradles.values():
            if cradle.baby_id:
                try:
                    self.analytics[cradle.baby_id] = (
                        await self.client.fetch_sleep_analytics(cradle)
                    )
                except Exception as err:
                    _LOGGER.debug("Analytics fetch failed for %s: %s", cradle.baby_id, err)

        return self.cradles
