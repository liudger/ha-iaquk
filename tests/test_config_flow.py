"""Test config flow for Indoor Air Quality UK Index integration."""

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.iaquk.config_flow import IaqukOptionsFlow
from custom_components.iaquk.const import (
    CONF_HUMIDITY,
    CONF_SOURCES,
    CONF_TEMPERATURE,
    CONF_TVOC,
    CONF_VOC_INDEX,
    DOMAIN,
)


async def test_form_user(hass: HomeAssistant) -> None:
    """Test user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}

    # Test with valid data
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test Air Quality",
            CONF_SOURCES: {
                CONF_TEMPERATURE: "sensor.temperature",
                CONF_HUMIDITY: "sensor.humidity",
            },
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Air Quality"
    assert result2["data"] == {
        CONF_NAME: "Test Air Quality",
        CONF_SOURCES: {
            CONF_TEMPERATURE: "sensor.temperature",
            CONF_HUMIDITY: "sensor.humidity",
        },
    }


async def test_form_user_no_sources(hass: HomeAssistant) -> None:
    """Test user form with no sources."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test Air Quality",
            CONF_SOURCES: {},
        },
    )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "no_sources"}


async def test_form_user_both_voc_sensors(hass: HomeAssistant) -> None:
    """Test user form with both VOC sensors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test Air Quality",
            CONF_SOURCES: {
                CONF_TVOC: "sensor.tvoc",
                CONF_VOC_INDEX: "sensor.voc_index",
            },
        },
    )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "only_one_voc_sensor"}


async def test_form_user_already_configured(hass: HomeAssistant) -> None:
    """Test user form with already configured name."""
    # First, create a config entry using the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test Air Quality",
            CONF_SOURCES: {
                CONF_TEMPERATURE: "sensor.temperature",
            },
        },
    )

    # Now try to create another with the same name
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_NAME: "Test Air Quality",
            CONF_SOURCES: {
                CONF_TEMPERATURE: "sensor.temperature",
            },
        },
    )

    assert result3["type"] == data_entry_flow.FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow - basic test that flow can be initialized."""
    # This is a basic test since options flow testing is complex
    # We're mainly verifying the options flow exists and imports correctly

    # Mock a config entry
    mock_entry = type("MockEntry", (), {
        "data": {CONF_SOURCES: {CONF_TEMPERATURE: "sensor.test"}},
        "entry_id": "test"
    })()

    options_flow = IaqukOptionsFlow(mock_entry)
    assert options_flow is not None
    assert options_flow.config_entry == mock_entry
