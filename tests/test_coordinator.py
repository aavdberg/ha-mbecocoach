"""Coordinator tests for rotating credentials and safe failure modes."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mbecocoach.api import EcoCoachAuthError, EcoCoachError
from custom_components.mbecocoach.const import CONF_EXPIRES_AT, CONF_REFRESH_TOKEN, CONF_TOKEN, CONF_VIN
from custom_components.mbecocoach.coordinator import EcoCoachCoordinator
from custom_components.mbecocoach.oauth import TokenSet

VIN = "WDD12345678901234"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_before_polling() -> None:
    """Update persisted credentials before using the new bearer for statistics."""
    hass = MagicMock()
    client = MagicMock()
    client.async_personal_statistics = AsyncMock()
    client.async_period_statistics = AsyncMock(return_value=(1, 2, 3))
    entry = MagicMock()
    entry.data = {
        CONF_VIN: VIN,
        CONF_TOKEN: "old",
        CONF_REFRESH_TOKEN: "old-refresh",
        CONF_EXPIRES_AT: time.time() - 1,
    }
    coordinator = EcoCoachCoordinator(hass, client, VIN, entry)
    with (
        patch("custom_components.mbecocoach.coordinator.async_get_clientsession"),
        patch("custom_components.mbecocoach.coordinator.refresh_tokens", new_callable=AsyncMock) as refresh,
    ):
        refresh.return_value = TokenSet("new", "new-refresh", time.time() + 3600)
        result = await coordinator._async_update_data()
    assert result.daily == 1
    refresh.assert_awaited_once()
    client.set_token.assert_called_once_with("new")
    persisted = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert persisted[CONF_TOKEN] == "new"
    assert persisted[CONF_REFRESH_TOKEN] == "new-refresh"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [(EcoCoachAuthError(), ConfigEntryAuthFailed), (EcoCoachError(), UpdateFailed)],
)
async def test_polling_errors(error: Exception, expected: type[Exception]) -> None:
    """Distinguish reauthentication from transient data failures."""
    client = MagicMock()
    client.async_personal_statistics = AsyncMock(side_effect=error)
    entry = MagicMock(data={CONF_VIN: VIN, CONF_TOKEN: "manual"})
    coordinator = EcoCoachCoordinator(MagicMock(), client, VIN, entry)
    with pytest.raises(expected):
        await coordinator._async_update_data()
