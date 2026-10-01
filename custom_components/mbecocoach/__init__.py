"""Mercedes Eco Coach integration."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EcoCoachClient
from .const import CONF_TOKEN, CONF_VIN
from .coordinator import EcoCoachCoordinator

type EcoCoachConfigEntry = ConfigEntry[EcoCoachCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EcoCoachConfigEntry) -> bool:
    """Set up statistics for a configured VIN."""
    client = EcoCoachClient(async_get_clientsession(hass), entry.data[CONF_TOKEN], ZoneInfo(hass.config.time_zone))
    coordinator = EcoCoachCoordinator(hass, client, entry.data[CONF_VIN])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcoCoachConfigEntry) -> bool:
    """Unload the integration."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
