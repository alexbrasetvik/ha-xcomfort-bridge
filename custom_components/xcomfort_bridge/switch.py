import logging
from typing import Optional

from xcomfort.devices import Rocker

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VERBOSE
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


def log(msg: str):
    if VERBOSE:
        _LOGGER.info(msg)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    hub = XComfortHub.get_hub(hass, entry)

    switches = list()
    for device in hub.devices:
        if isinstance(device, Rocker):
            _LOGGER.info(f"Adding {device}")
            switch = XComfortSwitch(hass, device)
            switches.append(switch)

    async_add_entities(switches)


class XComfortSwitch(SwitchEntity):
    def __init__(self, hass: HomeAssistant, device: Rocker):
        self.hass = hass

        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id

        self._unique_id = f"switch_{DOMAIN}_{device.device_id}"

    async def async_added_to_hass(self) -> None:
        self._device.state.subscribe(self._state_change)

    def _state_change(self, state) -> None:
        self._state = state
        should_update = self._state is not None

        if should_update:
            self.schedule_update_ha_state()
            # Emit event to enable stateless automation, since
            # actual switch state may be same as before
            self.hass.bus.fire(self._unique_id, {"on": state})

    @property
    def is_on(self) -> Optional[bool]:
        return self._state

    @property
    def name(self) -> str:
        return self._device.name_with_controlled

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        return False

    async def async_turn_on(self, **kwargs):
        raise NotImplementedError()

    async def async_turn_off(self, **kwargs):
        raise NotImplementedError()