"""Config flow for Eco Coach browser login or a manually supplied bearer token."""

from __future__ import annotations

import re
from typing import Any
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import EcoCoachAuthError, EcoCoachClient, EcoCoachConnectionError, EcoCoachError
from .const import CONF_EXPIRES_AT, CONF_REFRESH_TOKEN, CONF_TOKEN, CONF_VIN, DOMAIN
from .direct_login import EcoCoachMfaRequired, async_direct_login
from .oauth import OAuthAttempt, TokenSet, exchange_code

VIN_PATTERN = re.compile(r"[A-HJ-NPR-Z0-9]{17}\Z")
TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))


class EcoCoachConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Authorize Eco Coach in a browser or isolated CIAM session, or use a token."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Validate credentials and create an entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            vin = user_input[CONF_VIN].strip().upper()
            token = user_input.get(CONF_TOKEN, "").strip()
            if not VIN_PATTERN.fullmatch(vin):
                errors[CONF_VIN] = "invalid_vin"
            else:
                await self.async_set_unique_id(vin)
                self._abort_if_unique_id_configured()
                if token:
                    try:
                        await self._verify(vin, token)
                    except EcoCoachAuthError:
                        errors["base"] = "invalid_auth"
                    except EcoCoachConnectionError:
                        errors["base"] = "cannot_connect"
                    except EcoCoachError:
                        errors["base"] = "invalid_response"
                    else:
                        data = {CONF_VIN: vin, CONF_TOKEN: token}
                        return self.async_create_entry(title=f"Eco Coach {vin}", data=data)
                else:
                    self._vin = vin
                    if user_input.get("login_mode") == "direct":
                        return await self.async_step_direct()
                    return await self.async_step_authorize()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VIN): str,
                    vol.Optional(CONF_TOKEN): TOKEN_SELECTOR,
                    vol.Optional("login_mode", default="browser"): vol.In(
                        {"browser": "Browser login (confirmed)", "direct": "Direct login (experimental)"}
                    ),
                }
            ),
            errors=errors,
        )

    async def _verify(self, vin: str, token: str) -> None:
        client = EcoCoachClient(async_get_clientsession(self.hass), token, ZoneInfo(self.hass.config.time_zone))
        await client.async_personal_statistics(vin)
        await client.async_period_statistics(vin)

    async def async_step_authorize(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Offer a PKCE URL for a desktop browser; the callback stays in this flow."""
        self._attempt = OAuthAttempt()
        return await self.async_step_callback()

    def _finish_login(self, tokens: TokenSet) -> config_entries.ConfigFlowResult:
        """Store OAuth credentials, but never the username or password."""
        data = {
            CONF_VIN: self._vin,
            CONF_TOKEN: tokens.access_token,
            CONF_REFRESH_TOKEN: tokens.refresh_token,
            CONF_EXPIRES_AT: tokens.expires_at,
        }
        if hasattr(self, "_reauth_entry"):
            return self.async_update_reload_and_abort(self._reauth_entry, data=data)
        return self.async_create_entry(title=f"Eco Coach {self._vin}", data=data)

    async def async_step_direct(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Try an isolated CIAM session; never keep account credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]
            if not username or not password:
                errors["base"] = "invalid_auth"
            else:
                try:
                    tokens = await async_direct_login(self.hass, username, password)
                    await self._verify(self._vin, tokens.access_token)
                except EcoCoachMfaRequired:
                    errors["base"] = "mfa_required"
                except EcoCoachAuthError:
                    errors["base"] = "invalid_auth"
                except EcoCoachConnectionError:
                    errors["base"] = "cannot_connect"
                except EcoCoachError:
                    errors["base"] = "invalid_response"
                else:
                    return self._finish_login(tokens)
        return self.async_show_form(
            step_id="direct",
            data_schema=vol.Schema({vol.Required("username"): str, vol.Required("password"): TOKEN_SELECTOR}),
            errors=errors,
        )

    async def async_step_callback(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Accept only the full callback URL matching this PKCE session."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                tokens = await exchange_code(
                    async_get_clientsession(self.hass), self._attempt, user_input["callback_url"]
                )
                await self._verify(self._vin, tokens.access_token)
            except EcoCoachAuthError:
                errors["base"] = "invalid_auth"
            except EcoCoachConnectionError:
                errors["base"] = "cannot_connect"
            except EcoCoachError:
                errors["base"] = "invalid_response"
            else:
                return self._finish_login(tokens)
        return self.async_show_form(
            step_id="callback",
            data_schema=vol.Schema(
                {
                    vol.Optional("authorization_url", default=self._attempt.url): URL_SELECTOR,
                    vol.Required("callback_url"): TOKEN_SELECTOR,
                }
            ),
            description_placeholders={"authorization_url": self._attempt.url},
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Request a replacement token for the existing VIN."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Check and save a new token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input.get(CONF_TOKEN, "").strip()
            if not token:
                self._vin = self._reauth_entry.data[CONF_VIN]
                if user_input.get("login_mode") == "direct":
                    return await self.async_step_direct()
                return await self.async_step_authorize()
            else:
                try:
                    await self._verify(self._reauth_entry.data[CONF_VIN], token)
                except EcoCoachAuthError:
                    errors["base"] = "invalid_auth"
                except EcoCoachConnectionError:
                    errors["base"] = "cannot_connect"
                except EcoCoachError:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_update_reload_and_abort(
                        self._reauth_entry,
                        data_updates={CONF_TOKEN: token, CONF_REFRESH_TOKEN: None, CONF_EXPIRES_AT: None},
                    )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TOKEN): TOKEN_SELECTOR,
                    vol.Optional("login_mode", default="browser"): vol.In(
                        {"browser": "Browser login (confirmed)", "direct": "Direct login (experimental)"}
                    ),
                }
            ),
            errors=errors,
        )
