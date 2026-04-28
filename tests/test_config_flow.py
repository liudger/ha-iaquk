"""Test config flow for Indoor Air Quality UK Index integration."""

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.iaquk.config_flow import IaqukOptionsFlow
from custom_components.iaquk.const import (
    CONF_HUMIDITY,
    CONF_PM,
    CONF_SOURCES,
    CONF_TEMPERATURE,
    CONF_TVOC,
    CONF_VOC_INDEX,
    DOMAIN,
)


def _create_mock_device(hass: HomeAssistant, device_name: str = "VINDSTYRKA") -> str:
    """Create a mock source device."""
    config_entry = MockConfigEntry(domain="zha")
    config_entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("zha", device_name.lower())},
        manufacturer="IKEA of Sweden",
        name=device_name,
    )

    return device_entry.id


def _create_mock_sensor(
    hass: HomeAssistant,
    device_id: str,
    suggested_object_id: str,
    device_class: SensorDeviceClass | None = None,
    original_name: str | None = None,
) -> None:
    """Create a mock source sensor for a device."""
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor",
        "zha",
        suggested_object_id,
        suggested_object_id=suggested_object_id,
        device_id=device_id,
        original_device_class=device_class,
        original_name=original_name,
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


async def test_form_user_device_sources(hass: HomeAssistant) -> None:
    """Test user form auto-detects sources from a selected device."""
    device_id = _create_mock_device(hass)
    _create_mock_sensor(
        hass,
        device_id,
        "kitchen_temperature",
        SensorDeviceClass.TEMPERATURE,
    )
    _create_mock_sensor(
        hass,
        device_id,
        "kitchen_humidity",
        SensorDeviceClass.HUMIDITY,
    )
    _create_mock_sensor(
        hass,
        device_id,
        "kitchen_pm25",
        SensorDeviceClass.PM25,
    )
    _create_mock_sensor(
        hass,
        device_id,
        "kitchen_voc_index",
        original_name="VOC index",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Kitchen Air Quality",
            CONF_DEVICE_ID: device_id,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Kitchen Air Quality"
    assert result2["data"] == {
        CONF_NAME: "Kitchen Air Quality",
        CONF_DEVICE_ID: device_id,
        CONF_SOURCES: {
            CONF_TEMPERATURE: "sensor.kitchen_temperature",
            CONF_HUMIDITY: "sensor.kitchen_humidity",
            CONF_PM: ["sensor.kitchen_pm25"],
            CONF_VOC_INDEX: "sensor.kitchen_voc_index",
        },
    }


async def test_form_user_device_no_matching_sources(hass: HomeAssistant) -> None:
    """Test user form errors when a selected device has no supported sensors."""
    device_id = _create_mock_device(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Kitchen Air Quality",
            CONF_DEVICE_ID: device_id,
        },
    )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "no_matching_sources"}


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
    mock_entry = type(
        "MockEntry",
        (),
        {"data": {CONF_SOURCES: {CONF_TEMPERATURE: "sensor.test"}}, "entry_id": "test"},
    )()

    options_flow = IaqukOptionsFlow(mock_entry)
    result = await options_flow.async_step_init()
    assert result["type"] == data_entry_flow.FlowResultType.FORM
