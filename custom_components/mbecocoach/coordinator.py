"""Polling coordinator for Mercedes Eco Coach."""

from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EcoCoachAuthError, EcoCoachClient, EcoCoachData, EcoCoachError
from .const import CONF_EXPIRES_AT, CONF_REFRESH_TOKEN, CONF_TOKEN, UPDATE_INTERVAL
from .oauth import refresh_tokens

_LOGGER = logging.getLogger(__name__)


class EcoCoachCoordinator(DataUpdateCoordinator[EcoCoachData]):
    """Refresh the captured personal and period summaries every 15 minutes."""

    def __init__(self, hass: HomeAssistant, client: EcoCoachClient, vin: str, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, logger=_LOGGER, config_entry=entry, name="Eco Coach", update_interval=UPDATE_INTERVAL)
        self._client = client
        self._vin = vin
        self._entry = entry

    async def _async_update_data(self) -> EcoCoachData:
        """Retrieve the latest statistics."""
        try:
            refresh = self._entry.data.get(CONF_REFRESH_TOKEN)
            if refresh and time.time() >= self._entry.data.get(CONF_EXPIRES_AT, 0) - 60:
                tokens = await refresh_tokens(async_get_clientsession(self.hass), self._entry.data[CONF_REFRESH_TOKEN])
                self._client.set_token(tokens.access_token)
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    data={
                        **self._entry.data,
                        CONF_TOKEN: tokens.access_token,
                        CONF_REFRESH_TOKEN: tokens.refresh_token,
                        CONF_EXPIRES_AT: tokens.expires_at,
                    },
                )
            personal = await self._client.async_personal_statistics(self._vin)
            daily, weekly, monthly = await self._client.async_period_statistics(self._vin)
            return EcoCoachData(personal, daily, weekly, monthly)
        except EcoCoachAuthError as err:
            raise ConfigEntryAuthFailed("Eco Coach token expired or was rejected") from err
        except EcoCoachError as err:
            raise UpdateFailed(f"Eco Coach statistics update failed: {err}") from err
