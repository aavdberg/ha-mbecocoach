"""Mercedes Eco Coach integration."""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import ConfigEntrySelector, ConfigEntrySelectorConfig
from homeassistant.helpers.typing import ConfigType

from .api import EcoCoachClient
from .const import CONF_TOKEN, CONF_VIN, DOMAIN
from .coordinator import EcoCoachCoordinator

type EcoCoachConfigEntry = ConfigEntry[EcoCoachCoordinator]

_CARD_PATH = "/mbecocoach/mbecocoach-card.js"
_CARD_URL = f"{_CARD_PATH}?v=0.7.2"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the card route once, before config entries are set up."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_CARD_PATH, str(Path(__file__).parent / "frontend" / "mbecocoach-card.js"))]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EcoCoachConfigEntry) -> bool:
    """Set up statistics for a configured VIN."""
    client = EcoCoachClient(async_get_clientsession(hass), entry.data[CONF_TOKEN], ZoneInfo(hass.config.time_zone))
    coordinator = EcoCoachCoordinator(hass, client, entry.data[CONF_VIN], entry)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_initialize_history()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "event", "button"])
    loaded_entries: set[str] = hass.data.setdefault(DOMAIN, set())
    if not loaded_entries:
        add_extra_js_url(hass, _CARD_URL)
    loaded_entries.add(entry.entry_id)
    if not hass.services.has_service(DOMAIN, "get_points_history"):

        async def async_get_points_history(call: ServiceCall) -> dict:
            """Read a page from the selected local, minimal point history."""
            entries = hass.config_entries.async_entries(DOMAIN)
            selected = next((item for item in entries if item.entry_id == call.data["entry_id"]), None)
            if selected is None or selected.entry_id not in loaded_entries or selected.runtime_data.history is None:
                raise ValueError("Eco Coach points history is unavailable for this entry")
            return selected.runtime_data.history.page(call.data["offset"], call.data["limit"])

        hass.services.async_register(
            DOMAIN,
            "get_points_history",
            async_get_points_history,
            schema=vol.Schema(
                {
                    vol.Required("entry_id"): ConfigEntrySelector(ConfigEntrySelectorConfig(integration=DOMAIN)),
                    vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
                    vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                }
            ),
            supports_response=SupportsResponse.ONLY,
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcoCoachConfigEntry) -> bool:
    """Unload the integration."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["sensor", "event", "button"])
    if unloaded:
        loaded_entries: set[str] = hass.data[DOMAIN]
        loaded_entries.discard(entry.entry_id)
        if not loaded_entries:
            remove_extra_js_url(hass, _CARD_URL)
            hass.services.async_remove(DOMAIN, "get_points_history")
            hass.data.pop(DOMAIN)
    return unloaded
