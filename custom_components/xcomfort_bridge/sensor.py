"""Support for Xcomfort sensors."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import cast

from xcomfort.bridge import Room
from xcomfort.devices import RcTouch

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        rooms = hub.rooms
        devices = hub.devices

        _LOGGER.info(f"Found {len(rooms)} xcomfort rooms")
        _LOGGER.info(f"Found {len(devices)} xcomfort devices")

        sensors = list()
        for room in rooms:
            if room.state.value is not None:
                if room.state.value.power is not None:
                    _LOGGER.info(f"Adding power sensor for room {room.name}")
                    sensors.append(XComfortPowerSensor(hub, room))

                if room.state.value.temperature is not None:
                    _LOGGER.info(f"Adding temperature sensor for room {room.name}")
                    sensors.append(XComfortEnergySensor(hub, room))

        for device in devices:
            if isinstance(device, RcTouch):
                _LOGGER.info(f"Adding humidity sensor for device {device}")
                sensors.append(XComfortHumiditySensor(hub, device))

        _LOGGER.info(f"Added {len(sensors)} rc touch units")
        async_add_entities(sensors)

    asyncio.create_task(_wait_for_hub_then_setup())


class XComfortPowerSensor(SensorEntity):
    def __init__(self, hub: XComfortHub, room: Room):
        self._attr_device_class = SensorEntityDescription(
            key="current_consumption",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            state_class=SensorStateClass.MEASUREMENT,
            name="Current consumption",
        )
        self.hub = hub
        self._room = room
        self._attr_name = self._room.name
        self._attr_unique_id = f"energy_{self._room.room_id}"
        self._state = None
        self._room.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        should_update = self._state is not None

        self._state = state
        if should_update:
            self.async_write_ha_state()

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def native_unit_of_measurement(self):
        return UnitOfEnergy.WATT_HOUR

    @property
    def native_value(self):
        return self._state and self._state.power


class XComfortEnergySensor(RestoreSensor):
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, hub: XComfortHub, room: Room):
        self._attr_device_class = SensorEntityDescription(
            key="energy_used",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            name="Energy consumption",
        )
        self.hub = hub
        self._room = room
        self._attr_name = self._room.name
        self._attr_unique_id = f"energy_kwh_{self._room.room_id}"
        self._state = None
        self._room.state.subscribe(lambda state: self._state_change(state))
        self._updateTime = time.monotonic()
        self._consumption = 0

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        savedstate = await self.async_get_last_sensor_data()
        if savedstate:
            self._consumption = cast(float, savedstate.native_value)

    def _state_change(self, state):
        should_update = self._state is not None
        self._state = state
        if should_update:
            self.async_write_ha_state()

    def calculate(self):
        now = time.monotonic()
        timediff = math.floor(now - self._updateTime)  # number of seconds since last update
        self._consumption += (
            self._state.power / 3600 / 1000 * timediff
        )  # Calculate, in kWh, energy consumption since last update.
        self._updateTime = now

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def native_unit_of_measurement(self):
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        self.calculate()
        return self._consumption


class XComfortHumiditySensor(SensorEntity):
    def __init__(self, hub: XComfortHub, device: RcTouch):
        self._attr_device_class = SensorEntityDescription(
            key="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            name="Humidity",
        )
        self._device = device
        self._attr_name = self._device.name
        self._attr_unique_id = f"humidity_{self._device.name}_{self._device.device_id}"

        self.hub = hub
        self._state = None
        self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        should_update = self._state is not None

        self._state = state
        if should_update:
            self.async_write_ha_state()

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def native_unit_of_measurement(self):
        return PERCENTAGE

    @property
    def native_value(self):
        return self._state and self._state.humidity
