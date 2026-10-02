"""Unit tests for validation and reauthentication in the UI flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.mbecocoach.api import EcoCoachAuthError
from custom_components.mbecocoach.config_flow import EcoCoachConfigFlow
from custom_components.mbecocoach.const import CONF_EXPIRES_AT, CONF_REFRESH_TOKEN, CONF_TOKEN, CONF_VIN
from custom_components.mbecocoach.direct_login import EcoCoachMfaRequired
from custom_components.mbecocoach.oauth import TokenSet

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
        client.return_value.async_period_statistics = AsyncMock()
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
        client.return_value.async_period_statistics = AsyncMock()
        result = await flow.async_step_reauth_confirm({CONF_TOKEN: " replacement "})
    assert result == {"type": "abort"}
    assert flow.async_update_reload_and_abort.call_args.kwargs["data_updates"][CONF_TOKEN] == "replacement"


@pytest.mark.asyncio
async def test_browser_login_creates_entry() -> None:
    """New setup keeps PKCE in memory, validates both APIs and persists only tokens."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config.time_zone = "Europe/Amsterdam"
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    assert (await flow.async_step_user({CONF_VIN: VIN}))["type"] == "form"
    assert "code_challenge=" in flow.async_show_form.call_args.kwargs["description_placeholders"]["authorization_url"]
    schema = flow.async_show_form.call_args.kwargs["data_schema"]
    defaults = {key.schema: key.default() for key in schema.schema if isinstance(key, vol.Optional)}
    assert defaults["authorization_url"] == flow._attempt.url
    callback = f"ecocoach://login/callback?code=synthetic&state={flow._attempt.state}"
    with (
        patch("custom_components.mbecocoach.config_flow.exchange_code", new_callable=AsyncMock) as exchange,
        patch.object(flow, "_verify", new_callable=AsyncMock) as verify,
    ):
        exchange.return_value = TokenSet("access", "refresh", 10000)
        result = await flow.async_step_callback(
            {"authorization_url": "https://example.invalid/", "callback_url": callback}
        )
    assert result["type"] == "create_entry"
    verify.assert_awaited_once_with(VIN, "access")
    assert flow.async_create_entry.call_args.kwargs["data"] == {
        CONF_VIN: VIN,
        CONF_TOKEN: "access",
        CONF_REFRESH_TOKEN: "refresh",
        CONF_EXPIRES_AT: 10000,
    }


@pytest.mark.asyncio
async def test_browser_login_wrong_state_does_not_exchange() -> None:
    """A mismatched callback cannot acquire a token."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow.async_show_form = MagicMock(return_value={"type": "form", "errors": {"base": "invalid_auth"}})
    flow._vin = VIN
    await flow.async_step_authorize()
    with (
        patch("custom_components.mbecocoach.config_flow.async_get_clientsession"),
        patch("custom_components.mbecocoach.config_flow.exchange_code", new_callable=AsyncMock) as exchange,
    ):
        exchange.side_effect = EcoCoachAuthError()
        result = await flow.async_step_callback({"callback_url": "ecocoach://login/callback?code=bad&state=wrong"})
    assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_reauth_browser_login_updates_existing_entry() -> None:
    """Browser reauth replaces credentials without changing the VIN."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow._reauth_entry = MagicMock(data={CONF_VIN: VIN, CONF_TOKEN: "old"})
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    await flow.async_step_reauth_confirm({})
    with (
        patch("custom_components.mbecocoach.config_flow.async_get_clientsession"),
        patch("custom_components.mbecocoach.config_flow.exchange_code", new_callable=AsyncMock) as exchange,
        patch.object(flow, "_verify", new_callable=AsyncMock) as verify,
    ):
        exchange.return_value = TokenSet("new", "rotated", 10000)
        result = await flow.async_step_callback({"callback_url": "callback"})
    assert result["type"] == "abort"
    verify.assert_awaited_once_with(VIN, "new")
    assert flow.async_update_reload_and_abort.call_args.kwargs["data"] == {
        CONF_VIN: VIN,
        CONF_TOKEN: "new",
        CONF_REFRESH_TOKEN: "rotated",
        CONF_EXPIRES_AT: 10000,
    }


@pytest.mark.asyncio
async def test_direct_login_creates_entry_without_password() -> None:
    """Never persist either credential, while preserving the existing browser choice."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    result = await flow.async_step_user({CONF_VIN: VIN, "login_mode": "direct"})
    assert result["type"] == "form"
    with (
        patch("custom_components.mbecocoach.config_flow.async_direct_login", new_callable=AsyncMock) as login,
        patch.object(flow, "_verify", new_callable=AsyncMock) as verify,
    ):
        login.return_value = TokenSet("access", "refresh", 10000)
        result = await flow.async_step_direct({"username": " user@example.invalid ", "password": "passphrase"})
    assert result["type"] == "create_entry"
    login.assert_awaited_once_with(flow.hass, "user@example.invalid", "passphrase")
    verify.assert_awaited_once_with(VIN, "access")
    assert flow.async_create_entry.call_args.kwargs["data"] == {
        CONF_VIN: VIN,
        CONF_TOKEN: "access",
        CONF_REFRESH_TOKEN: "refresh",
        CONF_EXPIRES_AT: 10000,
    }


@pytest.mark.asyncio
async def test_direct_login_mfa_keeps_entry_unmodified() -> None:
    """Show an actionable error and retain existing credentials on MFA."""
    flow = EcoCoachConfigFlow()
    flow.hass = MagicMock()
    flow._reauth_entry = MagicMock(data={CONF_VIN: VIN, CONF_TOKEN: "old"})
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    await flow.async_step_reauth_confirm({"login_mode": "direct"})
    with patch("custom_components.mbecocoach.config_flow.async_direct_login", new_callable=AsyncMock) as login:
        login.side_effect = EcoCoachMfaRequired("MFA")
        await flow.async_step_direct({"username": "user", "password": "passphrase"})
    assert flow.async_show_form.call_args.kwargs["errors"]["base"] == "mfa_required"
    assert flow._reauth_entry.data[CONF_TOKEN] == "old"
