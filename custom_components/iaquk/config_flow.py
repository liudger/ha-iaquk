"""Config flow for Indoor Air Quality UK Index integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

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

PM_DEVICE_CLASSES = {
    SensorDeviceClass.PM1,
    SensorDeviceClass.PM10,
    SensorDeviceClass.PM25,
}
PM_DEVICE_CLASS_VALUES = {str(device_class) for device_class in PM_DEVICE_CLASSES}

SOURCE_DEVICE_CLASSES = {
    SensorDeviceClass.TEMPERATURE: CONF_TEMPERATURE,
    SensorDeviceClass.HUMIDITY: CONF_HUMIDITY,
    SensorDeviceClass.CO2: CONF_CO2,
    SensorDeviceClass.CO: CONF_CO,
    SensorDeviceClass.NITROGEN_DIOXIDE: CONF_NO2,
}

TVOC_DEVICE_CLASSES = {
    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
}
TVOC_DEVICE_CLASS_VALUES = {str(device_class) for device_class in TVOC_DEVICE_CLASSES}

DEVICE_SELECTOR = selector.DeviceSelector(
    selector.DeviceSelectorConfig(
        entity=selector.EntityFilterSelectorConfig(domain=SENSOR_DOMAIN),
    )
)

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


def _has_at_least_one_source(sources: dict[str, Any]) -> bool:
    """Check if at least one source is configured."""
    return any(sources.values())


def _validate_voc_sources(sources: dict[str, Any]) -> dict[str, str]:
    """Validate that only one of TVOC or VOC_INDEX is provided."""
    errors = {}

    if sources.get(CONF_TVOC) and sources.get(CONF_VOC_INDEX):
        errors["base"] = "only_one_voc_sensor"

    return errors


def _clean_sources(sources: dict[str, Any] | None) -> dict[str, Any]:
    """Remove empty source selections."""
    if not sources:
        return {}

    return {key: value for key, value in sources.items() if value}


def _entity_labels(entry: er.RegistryEntry) -> str:
    """Return searchable labels for an entity registry entry."""
    return " ".join(
        str(value).lower().replace("_", " ")
        for value in (
            entry.entity_id,
            entry.name,
            entry.original_name,
            entry.translation_key,
        )
        if value
    )


def _entity_device_classes(entry: er.RegistryEntry) -> set[str]:
    """Return all available device classes for an entity registry entry."""
    return {
        str(device_class)
        for device_class in (entry.device_class, entry.original_device_class)
        if device_class
    }


def _source_key_from_entry(labels: str, device_classes: set[str]) -> str | None:
    """Return a source key for an entity registry entry."""
    for device_class, source_key in SOURCE_DEVICE_CLASSES.items():
        if str(device_class) in device_classes:
            return source_key

    if "hcho" in labels or "formaldehyde" in labels:
        return CONF_HCHO
    if "radon" in labels:
        return CONF_RADON

    return None


def _is_voc_index_entry(labels: str) -> bool:
    """Return whether labels describe a VOC index sensor."""
    return "voc index" in labels or "vocindex" in labels


def _is_tvoc_entry(labels: str, device_classes: set[str]) -> bool:
    """Return whether labels or device classes describe a tVOC sensor."""
    return bool(device_classes & TVOC_DEVICE_CLASS_VALUES) or bool(
        "tvoc" in labels or "volatile organic" in labels
    )


def _sources_from_device(hass: HomeAssistant, device_id: str) -> dict[str, Any]:
    """Build source configuration from sensors attached to a device."""
    entity_registry = er.async_get(hass)
    sources: dict[str, Any] = {}
    pm_sources: list[str] = []
    tvoc_source = None
    voc_index_source = None

    for entry in er.async_entries_for_device(entity_registry, device_id):
        if entry.domain != SENSOR_DOMAIN:
            continue

        labels = _entity_labels(entry)
        device_classes = _entity_device_classes(entry)

        if device_classes & PM_DEVICE_CLASS_VALUES:
            pm_sources.append(entry.entity_id)
            continue

        if labels and not voc_index_source and _is_voc_index_entry(labels):
            voc_index_source = entry.entity_id
            continue

        if _is_tvoc_entry(labels, device_classes):
            tvoc_source = tvoc_source or entry.entity_id
            continue

        if source_key := _source_key_from_entry(labels, device_classes):
            sources.setdefault(source_key, entry.entity_id)

    if pm_sources:
        sources[CONF_PM] = sorted(pm_sources)

    if voc_index_source:
        sources[CONF_VOC_INDEX] = voc_index_source
    elif tvoc_source:
        sources[CONF_TVOC] = tvoc_source

    return sources


def _sources_from_input(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Build source configuration from a selected device and manual overrides."""
    sources = {}
    if device_id := user_input.get(CONF_DEVICE_ID):
        sources.update(_sources_from_device(hass, device_id))

    sources.update(_clean_sources(user_input.get(CONF_SOURCES)))
    return sources


def _unique_id_from_input(user_input: dict[str, Any]) -> str:
    """Return the config entry unique ID for the selected input."""
    if device_id := user_input.get(CONF_DEVICE_ID):
        return f"device:{device_id}"

    return user_input[CONF_NAME]


class IaqukConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Indoor Air Quality UK Index."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            sources = _sources_from_input(self.hass, user_input)

            # Validate that at least one source is provided
            if not _has_at_least_one_source(sources):
                errors["base"] = (
                    "no_matching_sources"
                    if user_input.get(CONF_DEVICE_ID)
                    else "no_sources"
                )
            else:
                # Validate VOC sources
                voc_errors = _validate_voc_sources(sources)
                errors.update(voc_errors)

            if not errors:
                # Create the config entry
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_SOURCES: sources,
                }
                if device_id := user_input.get(CONF_DEVICE_ID):
                    data[CONF_DEVICE_ID] = device_id

                await self.async_set_unique_id(_unique_id_from_input(user_input))
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
                    vol.Optional(CONF_DEVICE_ID): DEVICE_SELECTOR,
                    vol.Optional(CONF_SOURCES, default={}): SOURCE_SCHEMA,
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
        self._current_sources = config_entry.data.get(CONF_SOURCES, {})

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            sources = _clean_sources(user_input.get(CONF_SOURCES))

            # Validate that at least one source is provided
            if not _has_at_least_one_source(sources):
                errors["base"] = "no_sources"
            else:
                # Validate VOC sources
                voc_errors = _validate_voc_sources(sources)
                errors.update(voc_errors)

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SOURCES: sources,
                    },
                )

        # Get current configuration
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SOURCES, default=self._current_sources
                    ): SOURCE_SCHEMA,
                }
            ),
            errors=errors,
        )
