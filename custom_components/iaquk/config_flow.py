"""Config flow for Indoor Air Quality UK Index integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CO,
    CONF_CO2,
    CONF_HCHO,
    CONF_HUMIDITY,
    CONF_NO2,
    CONF_PM,
    CONF_RADON,
    CONF_SOURCES,
    CONF_TEMPERATURE,
    CONF_TVOC,
    CONF_VOC_INDEX,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Source configuration options
SOURCE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TEMPERATURE): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                device_class="temperature",
            )
        ),
        vol.Optional(CONF_HUMIDITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                device_class="humidity",
            )
        ),
        vol.Optional(CONF_CO2): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                device_class="carbon_dioxide",
            )
        ),
        vol.Optional(CONF_TVOC): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_VOC_INDEX): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_PM): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                device_class="pm25",
                multiple=True,
            )
        ),
        vol.Optional(CONF_NO2): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_CO): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                device_class="carbon_monoxide",
            )
        ),
        vol.Optional(CONF_HCHO): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_RADON): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
    }
)


def _has_at_least_one_source(user_input: dict[str, Any]) -> bool:
    """Check if at least one source is configured."""
    sources = user_input.get(CONF_SOURCES, {})
    return any(sources.values())


def _validate_voc_sources(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate that only one of TVOC or VOC_INDEX is provided."""
    sources = user_input.get(CONF_SOURCES, {})
    errors = {}

    if sources.get(CONF_TVOC) and sources.get(CONF_VOC_INDEX):
        errors["base"] = "only_one_voc_sensor"

    return errors


class IaqukConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Indoor Air Quality UK Index."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate that at least one source is provided
            if not _has_at_least_one_source(user_input):
                errors["base"] = "no_sources"
            else:
                # Validate VOC sources
                voc_errors = _validate_voc_sources(user_input)
                errors.update(voc_errors)

            if not errors:
                # Clean up empty sources
                sources = {k: v for k, v in user_input[CONF_SOURCES].items() if v}

                # Create the config entry
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_SOURCES: sources,
                }

                # Use the name as the unique ID
                await self.async_set_unique_id(user_input[CONF_NAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Indoor Air Quality"): str,
                    vol.Required(CONF_SOURCES): SOURCE_SCHEMA,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> IaqukOptionsFlow:
        """Create the options flow."""
        return IaqukOptionsFlow(config_entry)


class IaqukOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Indoor Air Quality UK Index."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Validate that at least one source is provided
            if not _has_at_least_one_source(user_input):
                errors["base"] = "no_sources"
            else:
                # Validate VOC sources
                voc_errors = _validate_voc_sources(user_input)
                errors.update(voc_errors)

            if not errors:
                # Clean up empty sources
                sources = {k: v for k, v in user_input[CONF_SOURCES].items() if v}

                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SOURCES: sources,
                    },
                )

        # Get current configuration
        current_sources = self.config_entry.data.get(CONF_SOURCES, {})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCES, default=current_sources): SOURCE_SCHEMA,
                }
            ),
            errors=errors,
        )
