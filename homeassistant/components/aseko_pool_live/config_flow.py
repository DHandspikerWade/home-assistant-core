"""Config flow for Aseko Pool Live integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from aioaseko import Aseko, AsekoAPIError, AsekoInvalidCredentials
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_UNIQUE_ID

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AsekoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aseko Pool Live."""

    VERSION = 2

    data_schema = vol.Schema(
        {
            vol.Required(CONF_EMAIL): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )

    reauth_entry: ConfigEntry

    async def get_account_info(self, email: str, password: str) -> dict:
        """Get account info from the mobile API and the web API."""
        aseko = Aseko(email, password)
        user = await aseko.login()
        return {
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
            CONF_UNIQUE_ID: user.user_id,
        }

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        errors = {}

        if user_input is not None:
            try:
                info = await self.get_account_info(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
            except AsekoAPIError:
                errors["base"] = "cannot_connect"
            except AsekoInvalidCredentials:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self.async_store_credentials(info)

        return self.async_show_form(
            step_id="user",
            data_schema=self.data_schema,
            errors=errors,
        )

    async def async_store_credentials(self, info: dict[str, Any]) -> ConfigFlowResult:
        """Store validated credentials."""

        if self.source == SOURCE_REAUTH:
            self.hass.config_entries.async_update_entry(
                self.reauth_entry,
                title=info[CONF_EMAIL],
                data={
                    CONF_EMAIL: info[CONF_EMAIL],
                    CONF_PASSWORD: info[CONF_PASSWORD],
                },
            )
            await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        await self.async_set_unique_id(info[CONF_UNIQUE_ID])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=info[CONF_EMAIL],
            data={
                CONF_EMAIL: info[CONF_EMAIL],
                CONF_PASSWORD: info[CONF_PASSWORD],
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""

        self.reauth_entry = self._get_reauth_entry()

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""

        errors = {}
        if user_input is not None:
            try:
                info = await self.get_account_info(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
            except AsekoAPIError:
                errors["base"] = "cannot_connect"
            except AsekoInvalidCredentials:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self.async_store_credentials(info)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.data_schema,
            errors=errors,
        )
