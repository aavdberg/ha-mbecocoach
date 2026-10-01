"""Unit tests for validation and reauthentication in the UI flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mbecocoach.api import EcoCoachAuthError
from custom_components.mbecocoach.config_flow import EcoCoachConfigFlow
from custom_components.mbecocoach.const import CONF_TOKEN, CONF_VIN

VIN = "WDD12345678901234"


@pytest.mark.asyncio
async def test_invalid_vin_skips_network() -> None:
    """Reject invalid VINs before constructing a request."""
    flow = EcoCoachConfigFlow()
    flow.async_show_form = MagicMock(return_value={"type": "form", "errors": {"vin": "invalid_vin"}})
    with patch("custom_components.mbecocoach.config_flow.async_get_clientsession") as session:
        result = await flow.async_step_user({CONF_VIN: "../not-a-vin", CONF_TOKEN: "secret"})
    assert result["errors"] == {"vin": "invalid_vin"}
    session.assert_not_called()


@pytest.mark.asyncio
async def test_valid_vin_creates_entry() -> None:
    """Validate token with the API before saving it."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config.time_zone = "Europe/Amsterdam"
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    with (
        patch("custom_components.mbecocoach.config_flow.async_get_clientsession"),
        patch("custom_components.mbecocoach.config_flow.EcoCoachClient") as client,
    ):
        client.return_value.async_personal_statistics = AsyncMock()
        result = await flow.async_step_user({CONF_VIN: VIN.lower(), CONF_TOKEN: " token "})
    assert result["type"] == "create_entry"
    client.return_value.async_personal_statistics.assert_awaited_once_with(VIN)
    assert flow.async_create_entry.call_args.kwargs["data"] == {CONF_VIN: VIN, CONF_TOKEN: "token"}


@pytest.mark.asyncio
async def test_rejected_token_is_not_saved() -> None:
    """Report an authentication error and keep the config entry unchanged."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config.time_zone = "Europe/Amsterdam"
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_show_form = MagicMock(return_value={"type": "form", "errors": {"base": "invalid_auth"}})
    with (
        patch("custom_components.mbecocoach.config_flow.async_get_clientsession"),
        patch("custom_components.mbecocoach.config_flow.EcoCoachClient") as client,
    ):
        client.return_value.async_personal_statistics = AsyncMock(side_effect=EcoCoachAuthError())
        result = await flow.async_step_user({CONF_VIN: VIN, CONF_TOKEN: "expired"})
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_reauth_updates_only_token() -> None:
    """Token replacement must retain the existing VIN."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config.time_zone = "Europe/Amsterdam"
    flow._reauth_entry = MagicMock(data={CONF_VIN: VIN, CONF_TOKEN: "old"})
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    with (
        patch("custom_components.mbecocoach.config_flow.async_get_clientsession"),
        patch("custom_components.mbecocoach.config_flow.EcoCoachClient") as client,
    ):
        client.return_value.async_personal_statistics = AsyncMock()
        result = await flow.async_step_reauth_confirm({CONF_TOKEN: " replacement "})
    assert result == {"type": "abort"}
    flow.async_update_reload_and_abort.assert_called_once_with(
        flow._reauth_entry, data_updates={CONF_TOKEN: "replacement"}
    )
