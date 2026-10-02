"""Polling coordinator for Mercedes Eco Coach."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EcoCoachAuthError, EcoCoachClient, EcoCoachData, EcoCoachError
from .const import CONF_EXPIRES_AT, CONF_REFRESH_TOKEN, CONF_TOKEN, UPDATE_INTERVAL
from .oauth import refresh_tokens
from .points_history import PointsHistory

_LOGGER = logging.getLogger(__name__)


class EcoCoachCoordinator(DataUpdateCoordinator[EcoCoachData]):
    """Refresh the captured personal and period summaries every 15 minutes."""

    def __init__(self, hass: HomeAssistant, client: EcoCoachClient, vin: str, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, logger=_LOGGER, config_entry=entry, name="Eco Coach", update_interval=UPDATE_INTERVAL)
        self._client = client
        self._vin = vin
        self._entry = entry
        self.history: PointsHistory | None = None
        self._history_lock = asyncio.Lock()

    async def async_initialize_history(self) -> None:
        """Fetch old awards once on installation, then use the private local cache."""
        history = PointsHistory(self.hass, self._entry.entry_id)
        if await history.async_load():
            await history.async_merge(self.data.awards)
        else:
            try:
                await history.async_replace(await self._client.async_awards(self._vin, all_history=True))
            except EcoCoachAuthError as err:
                raise ConfigEntryAuthFailed("Eco Coach rejected the points history request") from err
            except EcoCoachError as err:
                raise ConfigEntryNotReady("Eco Coach points history could not be fetched") from err
        self.history = history

    async def async_replace_history(self) -> None:
        """Manually re-import all points without changing HA recorder history."""
        if self.history is None:
            raise EcoCoachError("Points history has not been initialized")
        async with self._history_lock:
            awards = await self._client.async_awards(self._vin, all_history=True)
            await self.history.async_replace(awards)
            self.async_set_updated_data(self.data)

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
            points = await self._client.async_points()
            awards = await self._client.async_awards(self._vin)
            if self.history is not None:
                async with self._history_lock:
                    await self.history.async_merge(awards)
            return EcoCoachData(personal, daily, weekly, monthly, points, awards)
        except EcoCoachAuthError as err:
            raise ConfigEntryAuthFailed("Eco Coach token expired or was rejected") from err
        except EcoCoachError as err:
            raise UpdateFailed(f"Eco Coach statistics update failed: {err}") from err
