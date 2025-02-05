"""Config flow for Discovergy integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pydiscovergy import Discovergy
from pydiscovergy.authentication import BasicAuth
import pydiscovergy.error as discovergyError
import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_EMAIL,
        ): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.EMAIL,
                autocomplete="email",
            )
        ),
        vol.Required(
            CONF_PASSWORD,
        ): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        ),
    }
)


class DiscovergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Discovergy."""

    VERSION = 1

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate user input and create config entry."""
        errors = {}

        if user_input:
            try:
                await Discovergy(
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    httpx_client=get_async_client(self.hass),
                    authentication=BasicAuth(),
                ).meters()
            except (discovergyError.HTTPError, discovergyError.DiscovergyClientError):
                errors["base"] = "cannot_connect"
            except discovergyError.InvalidLogin:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error occurred while getting meters")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())

                if self.source == SOURCE_REAUTH:
                    self._abort_if_unique_id_mismatch(reason="account_mismatch")
                    return self.async_update_reload_and_abort(
                        entry=self._get_reauth_entry(),
                        data_updates={
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )

                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CONFIG_SCHEMA,
                self._get_reauth_entry().data
                if self.source == SOURCE_REAUTH
                else user_input,
            ),
            errors=errors,
        )
