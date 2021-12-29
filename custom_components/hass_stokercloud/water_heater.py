from __future__ import annotations
from homeassistant.const import CONF_USERNAME
import logging

from homeassistant.components.water_heater import (
    SUPPORT_AWAY_MODE,
    SUPPORT_OPERATION_MODE,
    WaterHeaterEntity,
)
from homeassistant.const import PRECISION_TENTHS, PRECISION_WHOLE, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .mixins import StokerCloudControllerMixin

from stokercloud.controller_data import State

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    client = hass.data[DOMAIN][config.entry_id]
    serial = config.data[CONF_USERNAME]
    async_add_entities([
        StokerCloudWaterHeater(client, serial, 'Hot Water', ''),
    ])


class StokerCloudWaterHeater(StokerCloudControllerMixin, WaterHeaterEntity):
    @property
    def current_operation(self) -> str:
        if self.client.controller_data().state == State.HOT_WATER:
            return STATE_ON
        return STATE_OFF

    @property
    def current_temperature(self):
        return self.client.controller_data().hotwater_temperature_current

    @property
    def target_temperature(self):
        return self.client.controller_data().hotwater_temperature_requested