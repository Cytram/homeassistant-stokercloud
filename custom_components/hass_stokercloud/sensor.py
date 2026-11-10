"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from stokercloud.controller_data import PowerState, Unit, Value
from stokercloud.client import Client as StokerCloudClient

import datetime
from homeassistant.const import (
    CONF_USERNAME,
    PERCENTAGE,
    UnitOfLength,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from .const import DOMAIN
from .mixins import StokerCloudControllerMixin

import logging

logger = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(minutes=1)

UNIT_MAP = {
    Unit.KWH: UnitOfPower.KILO_WATT,  # the API reports current power as "kwh"
    Unit.KW: UnitOfPower.KILO_WATT,
    Unit.DEGREE: UnitOfTemperature.CELSIUS,
    Unit.KILO_GRAM: UnitOfMass.KILOGRAMS,
    Unit.GRAM: UnitOfMass.GRAMS,
    Unit.CM: UnitOfLength.CENTIMETERS,
    Unit.PERCENT: PERCENTAGE,
    Unit.PASCAL: UnitOfPressure.PA,
    Unit.HPA: UnitOfPressure.HPA,
    Unit.METER_PER_SECOND: UnitOfSpeed.METERS_PER_SECOND,
    Unit.M3_HOUR: UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
}

TEMP = SensorDeviceClass.TEMPERATURE
MEAS = SensorStateClass.MEASUREMENT


async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    client = hass.data[DOMAIN][config.entry_id]
    serial = config.data[CONF_USERNAME]

    def sensor(name, key, device_class=None, state_class=MEAS, enabled=True):
        return StokerCloudControllerSensor(client, serial, name, key, device_class, state_class, enabled)

    async_add_entities([
        StokerCloudControllerBinarySensor(client, serial, 'Running', 'running', 'power'),
        StokerCloudControllerBinarySensor(client, serial, 'Alarm', 'alarm', 'problem'),
        StokerCloudOutputBinarySensor(client, serial, 'Boiler Pump', 'boiler_pump', 'running'),
        StokerCloudControllerSensor(client, serial, 'Boiler Temperature', 'boiler_temperature_current',
                                    SensorDeviceClass.TEMPERATURE),
        StokerCloudControllerSensor(client, serial, 'Boiler Temperature Requested', 'boiler_temperature_requested',
                                    SensorDeviceClass.TEMPERATURE),
        StokerCloudControllerSensor(client, serial, 'Boiler Return Temperature', 'boiler_return_temperature',
                                    SensorDeviceClass.TEMPERATURE),
        StokerCloudControllerSensor(client, serial, 'Boiler Effect', 'boiler_kwh', SensorDeviceClass.POWER),
        StokerCloudControllerSensor(client, serial, 'Total Consumption', 'consumption_total',
                                    state_class=SensorStateClass.TOTAL_INCREASING),
        StokerCloudControllerSensor(client, serial, 'Daily Consumption', 'consumption_day', SensorDeviceClass.WEIGHT),
        StokerCloudControllerSensor(client, serial, 'Hopper Capacity', 'hopper_capacity', SensorDeviceClass.DISTANCE),
        StokerCloudControllerSensor(client, serial, 'State', 'state'),

        # boiler
        sensor('Power', 'power_percent'),
        sensor('Smoke Temperature', 'smoke_temperature', TEMP),
        sensor('Drop Shaft Temperature', 'drop_shaft_temperature', TEMP),
        sensor('Photo Sensor', 'photo_sensor'),
        sensor('Oxygen', 'oxygen'),
        sensor('Oxygen Requested', 'oxygen_requested'),
        sensor('Oxygen Regulation Low', 'oxygen_regulation_low'),
        sensor('Oxygen Regulation Mid', 'oxygen_regulation_mid'),
        sensor('Oxygen Regulation High', 'oxygen_regulation_high'),
        sensor('Boiler Pressure', 'pressure', SensorDeviceClass.PRESSURE),
        sensor('Exhaust Fan', 'exhaust_fan'),
        sensor('Online Time', 'online_time'),
        sensor('Ash Level', 'ash_distance'),
        sensor('Air Requested', 'air_requested', enabled=False),
        sensor('Back Pressure', 'back_pressure', enabled=False),
        sensor('Substate', 'substate', state_class=None, enabled=False),

        # hopper / auger
        sensor('Hopper Content', 'hopper_content', SensorDeviceClass.WEIGHT),
        sensor('Hopper Level', 'hopper_level'),
        sensor('Auger Capacity', 'auger_capacity', SensorDeviceClass.WEIGHT),
        sensor('Auger Low', 'auger_low'),
        sensor('Auger High', 'auger_high'),
        sensor('Trip 1', 'trip_1', SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL),
        sensor('Trip 2', 'trip_2', SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL),
        sensor('Power 10%', 'power_10_percent', SensorDeviceClass.POWER, enabled=False),
        sensor('Power 100%', 'power_100_percent', SensorDeviceClass.POWER, enabled=False),

        # hot water
        sensor('Hot Water Difference', 'hotwater_difference', TEMP, enabled=False),

        # weather (from StokerCloud's weather service, not a sensor on the boiler)
        sensor('Outdoor Temperature', 'outdoor_temperature', TEMP),
        sensor('Wind Speed', 'wind_speed', SensorDeviceClass.WIND_SPEED),
        sensor('Wind Direction', 'wind_direction', state_class=None),
        sensor('Clouds', 'clouds'),
        sensor('Humidity', 'humidity', SensorDeviceClass.HUMIDITY),
        sensor('Air Pressure', 'air_pressure', SensorDeviceClass.ATMOSPHERIC_PRESSURE),

        StokerCloudInfoMessagesSensor(client, serial, 'Info Messages', 'info_messages'),
    ])


class StokerCloudControllerBinarySensor(StokerCloudControllerMixin, BinarySensorEntity):
    """Representation of a Sensor."""

    def __init__(self, client: StokerCloudClient, serial, name: str, client_key: str, device_class):
        """Initialize the sensor."""
        super(StokerCloudControllerBinarySensor, self).__init__(client, serial, name, client_key)
        self._device_class = device_class

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self._state is PowerState.ON

    @property
    def device_class(self):
        return self._device_class


class StokerCloudOutputBinarySensor(StokerCloudControllerMixin, BinarySensorEntity):
    """On/off output on the controller, e.g. the boiler pump."""

    def __init__(self, client: StokerCloudClient, serial, name: str, output_name: str, device_class):
        super().__init__(client, serial, name, None)
        self._output_name = output_name
        self._device_class = device_class

    @property
    def is_on(self):
        if self.controller_data:
            output = self.controller_data.outputs.get(self._output_name)
            if output is not None:
                return output.is_on

    @property
    def available(self):
        if self.controller_data is None:
            return True
        output = self.controller_data.outputs.get(self._output_name)
        return output is not None and output.enabled

    @property
    def device_class(self):
        return self._device_class


class StokerCloudControllerSensor(StokerCloudControllerMixin, SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, client: StokerCloudClient, serial, name: str, client_key: str, device_class=None,
                 state_class=None, enabled=True):
        """Initialize the sensor."""
        super(StokerCloudControllerSensor, self).__init__(client, serial, name, client_key)
        self._device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_registry_enabled_default = enabled

    @property
    def device_class(self):
        return self._device_class

    @property
    def native_value(self):
        """Return the value reported by the sensor."""
        if self._state is not None:
            if isinstance(self._state, Value):
                return self._state.value
            return self._state

    @property
    def native_unit_of_measurement(self):
        if self._state is not None and isinstance(self._state, Value):
            return UNIT_MAP.get(self._state.unit)


class StokerCloudInfoMessagesSensor(StokerCloudControllerMixin, SensorEntity):
    """Number of active info messages; the messages are in the attributes."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self._state is not None:
            return len(self._state)

    @property
    def extra_state_attributes(self):
        if not self._state:
            return {"messages": []}
        return {
            "messages": [
                {
                    "id": m.id,
                    "text": m.text,
                    "value": m.value,
                    "unit": m.unit,
                }
                for m in self._state
            ]
        }
