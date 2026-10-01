"""Polling coordinator for Mercedes Eco Coach."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EcoCoachAuthError, EcoCoachClient, EcoCoachError, PersonalStatistics
from .const import UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EcoCoachCoordinator(DataUpdateCoordinator[PersonalStatistics]):
    """Refresh personal statistics every 15 minutes."""

    def __init__(self, hass: HomeAssistant, client: EcoCoachClient, vin: str) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, logger=_LOGGER, name="Eco Coach", update_interval=UPDATE_INTERVAL)
        self._client = client
        self._vin = vin

    async def _async_update_data(self) -> PersonalStatistics:
        """Retrieve the latest statistics."""
        try:
            return await self._client.async_personal_statistics(self._vin)
        except EcoCoachAuthError as err:
            raise ConfigEntryAuthFailed("Eco Coach token expired or was rejected") from err
        except EcoCoachError as err:
            raise UpdateFailed(f"Eco Coach statistics update failed: {err}") from err
