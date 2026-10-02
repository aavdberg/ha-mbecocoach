"""Card module registration follows integration entry lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mbecocoach import async_setup_entry, async_unload_entry
from custom_components.mbecocoach.const import CONF_TOKEN, CONF_VIN, DOMAIN


@pytest.mark.asyncio
async def test_card_is_served_once_and_loaded_while_any_entry_is_active() -> None:
    """No dashboard modification; load one module for any number of vehicles."""
    hass = MagicMock()
    hass.data = {}
    hass.config.time_zone = "Europe/Amsterdam"
    hass.http.async_register_static_paths = AsyncMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.services.has_service.return_value = True
    first = MagicMock(entry_id="first", data={CONF_VIN: "WDD12345678901234", CONF_TOKEN: "synthetic"})
    second = MagicMock(entry_id="second", data={CONF_VIN: "WDD12345678901235", CONF_TOKEN: "synthetic"})

    with (
        patch("custom_components.mbecocoach.EcoCoachCoordinator") as coordinator,
        patch("custom_components.mbecocoach.add_extra_js_url") as add_js,
        patch("custom_components.mbecocoach.remove_extra_js_url") as remove_js,
        patch("custom_components.mbecocoach.async_get_clientsession"),
    ):
        coordinator.return_value.async_config_entry_first_refresh = AsyncMock()
        coordinator.return_value.async_initialize_history = AsyncMock()
        await async_setup_entry(hass, first)
        await async_setup_entry(hass, second)
        hass.http.async_register_static_paths.assert_awaited_once()
        paths = hass.http.async_register_static_paths.await_args.args[0]
        assert len(paths) == 1
        assert paths[0].url_path == "/mbecocoach/mbecocoach-card.js"
        assert paths[0].path.endswith("mbecocoach-card.js")
        add_js.assert_called_once()
        assert add_js.call_args.args[1].startswith("/mbecocoach/mbecocoach-card.js?v=")
        assert hass.data[DOMAIN] == {"first", "second"}
        await async_unload_entry(hass, first)
        remove_js.assert_not_called()
        await async_unload_entry(hass, second)
        remove_js.assert_called_once_with(hass, add_js.call_args.args[1])
        await async_setup_entry(hass, first)
        hass.http.async_register_static_paths.assert_awaited_once()
        assert add_js.call_count == 2
