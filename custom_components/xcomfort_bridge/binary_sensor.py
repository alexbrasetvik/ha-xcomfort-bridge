import logging

from xcomfort.devices import DoorSensor, DoorWindowSensor, WindowSensor

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    hub = XComfortHub.get_hub(hass, entry)

    devices = hub.devices

    sensors = list()

    for device in devices:
        if isinstance(device, DoorWindowSensor):
            sensors.append(XComfortDoorWindowSensor(device))

    async_add_entities(sensors)


class XComfortDoorWindowSensor(BinarySensorEntity):
    def __init__(self, device: WindowSensor | DoorSensor) -> None:
        """Initialize the unit binary sensor."""
        super().__init__()
        self._attr_name = device.name
        self._attr_unique_id = f"xcomfort-{device.device_id}"
        self._device = device
        self._attr_state = device.is_open

        if isinstance(device, WindowSensor):
            self._attr_device_class = BinarySensorDeviceClass.WINDOW
        elif isinstance(device, DoorSensor):
            self._attr_device_class = BinarySensorDeviceClass.DOOR

    async def async_added_to_hass(self):
        if self._device.state is not None:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state: bool):
        self._attr_state = state
        self.schedule_update_ha_state()

    @property
    def is_on(self) -> bool | None:
        return self._device and self._device.is_open