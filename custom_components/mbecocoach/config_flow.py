"""Config flow for a manually supplied Eco Coach bearer token."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import EcoCoachAuthError, EcoCoachClient, EcoCoachConnectionError, EcoCoachError
from .const import CONF_TOKEN, CONF_VIN, DOMAIN

VIN_PATTERN = re.compile(r"[A-HJ-NPR-Z0-9]{17}\Z")
TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class EcoCoachConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Collect VIN and an existing bearer token."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Validate credentials and create an entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            vin = user_input[CONF_VIN].strip().upper()
            token = user_input[CONF_TOKEN].strip()
            if not VIN_PATTERN.fullmatch(vin):
                errors[CONF_VIN] = "invalid_vin"
            elif not token:
                errors[CONF_TOKEN] = "invalid_token"
            else:
                await self.async_set_unique_id(vin)
                self._abort_if_unique_id_configured()
                try:
                    await EcoCoachClient(async_get_clientsession(self.hass), token).async_personal_statistics(vin)
                except EcoCoachAuthError:
                    errors["base"] = "invalid_auth"
                except EcoCoachConnectionError:
                    errors["base"] = "cannot_connect"
                except EcoCoachError:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(title=f"Eco Coach {vin}", data={CONF_VIN: vin, CONF_TOKEN: token})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_VIN): str, vol.Required(CONF_TOKEN): TOKEN_SELECTOR}),
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
            token = user_input[CONF_TOKEN].strip()
            if not token:
                errors["base"] = "invalid_auth"
            else:
                try:
                    await EcoCoachClient(async_get_clientsession(self.hass), token).async_personal_statistics(
                        self._reauth_entry.data[CONF_VIN]
                    )
                except EcoCoachAuthError:
                    errors["base"] = "invalid_auth"
                except EcoCoachConnectionError:
                    errors["base"] = "cannot_connect"
                except EcoCoachError:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_update_reload_and_abort(self._reauth_entry, data_updates={CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): TOKEN_SELECTOR}),
            errors=errors,
        )
