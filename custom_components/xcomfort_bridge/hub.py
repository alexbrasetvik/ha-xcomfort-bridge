"""Class used to communicate with xComfort bridge."""

from __future__ import annotations

import asyncio
import logging

from xcomfort.bridge import Bridge

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERBOSE

_LOGGER = logging.getLogger(__name__)

"""Logging function."""


def log(msg: str):
    if VERBOSE:
        _LOGGER.info(msg)


"""Wrapper class over bridge library to emulate hub."""


class XComfortHub:
    def __init__(
        self,
        hass: HomeAssistant,
        identifier: str,
        ip: str,
        auth_key: str,
        id_version: int = 2,
        unique_id: str | None = None,
    ):
        """Initialize underlying bridge"""
        bridge = Bridge(ip, auth_key)
        self.hass = hass
        self.bridge = bridge
        self.identifier = identifier
        if self.identifier is None:
            self.identifier = ip

        self.unique_id = unique_id or self.identifier
        self.id_version = id_version
        self.devices = list()
        self._loop = asyncio.get_event_loop()

        self.has_done_initial_load = asyncio.Event()

    def start(self):
        """Starts the event loop running the bridge."""
        self.hass.async_create_task(self.bridge.run())

    async def stop(self):
        """Stops the bridge event loop.
        Will also shut down websocket, if open.
        """
        self.has_done_initial_load.clear()
        await self.bridge.close()

    async def load_devices(self):
        """Loads devices from bridge."""
        log("loading devices")
        devs = await self.bridge.get_devices()
        self.devices = devs.values()

        log(f"loaded {len(self.devices)} devices")

        log("loading rooms")

        rooms = await self.bridge.get_rooms()
        self.rooms = rooms.values()

        log(f"loaded {len(self.rooms)} rooms")

        self.has_done_initial_load.set()

    @property
    def hub_id(self) -> str:
        if self.id_version == 1:
            return self.bridge.ip_address
        return self.unique_id

    @staticmethod
    def get_hub(hass: HomeAssistant, entry: ConfigEntry) -> XComfortHub:
        return hass.data[DOMAIN][entry.entry_id]
